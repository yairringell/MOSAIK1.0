#!/usr/bin/env python3
"""
Polygon Duplicator Application
A simple PyQt5 application with a central canvas and side panels for polygon editing.
"""

import sys
import csv
import json
import math
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QFrame, QLabel, QPushButton, QFileDialog, QCheckBox, QSpinBox, QLineEdit, QInputDialog, QMessageBox
)
from PyQt5.QtCore import Qt, QPoint, QTimer
from PyQt5.QtGui import QPainter, QColor, QPen, QPixmap, QBrush, QFont, QPolygon, QCursor


class Canvas(QWidget):
    """Central canvas widget for drawing/displaying content"""
    
    def __init__(self):
        super().__init__()
        self.setMinimumSize(600, 600)
        self.setStyleSheet("background-color: white; border: 1px solid black;")
        self.background_image = None
        self.original_background_image = None  # Store original image for scaling
        self.current_x_scale = 1.0  # Current X scale factor
        self.current_y_scale = 1.0  # Current Y scale factor
        
        # Polygon drawing mode variables
        self.polygon_mode = False
        self.polygon_points = []  # Points for the current polygon being drawn
        self.polygon_cursor_size = 10  # Size of the square cursor in pixels
        self.polygons = []  # List of completed polygons
        
        # Zoom and pan variables
        self.zoom_factor = 1.0
        self.pan_offset_x = 0.0
        self.pan_offset_y = 0.0
        self.is_panning = False
        self.last_pan_point = None
        
        # Image offset variables (separate from zoom/pan)
        self.image_offset_x = 0
        self.image_offset_y = 0
        
        # Eraser mode
        self.eraser_mode = False
        self.is_erasing = False  # Track if currently dragging to erase
        
        # Duplicate mode
        self.duplicate_mode = False  # Whether to create 8 copies of each polygon
        self.next_group_id = 1  # Counter for assigning group IDs to duplicate sets
        
        # Center point offset
        self.center_offset_x = 0
        self.center_offset_y = 0
        
        # Selection tracking
        self.selected_polygon_index = -1  # Index of currently selected polygon (-1 means none)
        
        # Control point editing
        self.selected_control_point = -1  # Index of selected control point (-1 means none)
        self.is_dragging_control_point = False
        self.control_point_size = 8  # Size of control point circles in pixels
        
        # Circle drawing
        # Image drag handle
        self.is_dragging_image = False
        self.image_drag_start_offset_x = 0
        self.image_drag_start_offset_y = 0
        self.drag_handle_size = 12  # Size of the drag handle circle
        
        # Image visibility
        self.show_image = True  # Default to showing image
        
        # Grid variables
        self.show_grid = False  # Whether to show the grid
        self.grid_size = 300  # Size of each individual grid box/cell in world coordinates (increased for 3x3)
        self.grid_offset_x = 0  # Grid offset in world coordinates
        self.grid_offset_y = 0  # Grid offset in world coordinates
        self.grid_dragging = False  # Whether we're dragging the grid
        self.grid_drag_start = None  # Starting point for grid drag
        self.grid_drag_world_start = None  # Starting world coordinates for grid drag
        
        # Enable mouse tracking for cursor display
        self.setMouseTracking(True)
        
        # Enable keyboard focus for key events
        self.setFocusPolicy(Qt.StrongFocus)
        
        # Timer for cursor updates in polygon mode
        self.cursor_timer = QTimer()
        self.cursor_timer.timeout.connect(self.update_cursor)
        # Don't start timer by default - only when entering polygon mode
    
    def update_cursor(self):
        """Update cursor display in polygon mode"""
        if self.polygon_mode:
            self.update()  # Refresh display to show cursor
    
    def screen_to_world(self, screen_x, screen_y):
        """Convert screen coordinates to world coordinates"""
        world_x = (screen_x - self.pan_offset_x) / self.zoom_factor
        world_y = (screen_y - self.pan_offset_y) / self.zoom_factor
        return world_x, world_y
    
    def world_to_screen(self, world_x, world_y):
        """Convert world coordinates to screen coordinates"""
        screen_x = world_x * self.zoom_factor + self.pan_offset_x
        screen_y = world_y * self.zoom_factor + self.pan_offset_y
        return screen_x, screen_y
    
    def set_eraser_mode(self, enabled):
        """Set whether eraser mode is enabled"""
        self.eraser_mode = enabled
        if enabled:
            # Exit polygon mode if active
            if self.polygon_mode:
                self.polygon_mode = False
                self.polygon_points = []  # Clear any in-progress polygon
                self.cursor_timer.stop()
                
                # Update polygon checkbox to reflect the change
                parent = self.parent()
                while parent:
                    for child in parent.findChildren(QCheckBox):
                        if child.text() == "Polygon" and hasattr(child, 'setChecked'):
                            child.blockSignals(True)
                            child.setChecked(False)
                            child.blockSignals(False)
                            break
                    parent = parent.parent()
            
            # Set cursor to indicate eraser mode
            self.setCursor(Qt.PointingHandCursor)
        else:
            # Reset cursor
            self.setCursor(Qt.ArrowCursor if not self.polygon_mode else Qt.BlankCursor)
        self.update()  # Refresh display
    
    def set_image_visible(self, visible):
        """Set whether to show the background image"""
        self.show_image = visible
        self.update()  # Refresh display
    
    def get_image_drag_handle_position(self):
        """Get the screen position of the image drag handle (bottom-left of image)"""
        if (not self.show_image or 
            not self.background_image or 
            self.background_image.isNull()):
            return None, None
        
        # Get image position in world coordinates
        image_world_x = self.image_offset_x
        image_world_y = self.image_offset_y
        
        # Get image dimensions in world coordinates
        image_world_width = self.background_image.width()
        image_world_height = self.background_image.height()
        
        # Bottom-left corner of image in world coordinates
        bottom_left_world_x = image_world_x
        bottom_left_world_y = image_world_y + image_world_height
        
        # Convert to screen coordinates
        handle_x, handle_y = self.world_to_screen(bottom_left_world_x, bottom_left_world_y)
        
        return handle_x, handle_y
    
    def is_point_in_image_drag_handle(self, screen_x, screen_y):
        """Check if a screen point is inside the image drag handle"""
        handle_x, handle_y = self.get_image_drag_handle_position()
        if handle_x is None or handle_y is None:
            return False
        
        # Check if point is within handle circle
        distance = math.sqrt((screen_x - handle_x)**2 + (screen_y - handle_y)**2)
        return distance <= self.drag_handle_size / 2
    
    def set_background_image(self, image_path, desired_size=None):
        """Set background image for the canvas, optionally resizing it"""
        try:
            # Load the original image
            original_pixmap = QPixmap(image_path)
            
            # Store the original image for scaling
            self.original_background_image = original_pixmap
            self.current_x_scale = 1.0  # Reset X scale to 100%
            self.current_y_scale = 1.0  # Reset Y scale to 100%
            
            if desired_size is not None:
                # Get original dimensions
                original_width = original_pixmap.width()
                original_height = original_pixmap.height()
                
                # Determine which side is longer
                longer_side = max(original_width, original_height)
                
                # Calculate scale factor
                scale_factor = desired_size / longer_side
                
                # Calculate new dimensions maintaining aspect ratio
                new_width = int(original_width * scale_factor)
                new_height = int(original_height * scale_factor)
                
                # Resize the image
                self.background_image = original_pixmap.scaled(
                    new_width, new_height, 
                    Qt.KeepAspectRatio, 
                    Qt.SmoothTransformation
                )
            else:
                # Use original size
                self.background_image = original_pixmap
            
            # Center the grid on the loaded image
            self.center_grid_on_image()
            
            self.update()  # Trigger repaint
            return True
        except Exception as e:
            print(f"Error loading image: {e}")
            return False
    
    def center_grid_on_image(self):
        """Center the 3x3 grid on the loaded image"""
        if not self.background_image or self.background_image.isNull():
            return
        
        # Get image dimensions
        image_width = self.background_image.width()
        image_height = self.background_image.height()
        
        # Calculate the total grid size (3 cells * cell size)
        total_grid_size = self.grid_size * 3
        
        # Calculate the center position of the image
        image_center_x = image_width / 2
        image_center_y = image_height / 2
        
        # Calculate grid offset to center it on the image
        # The grid offset is the top-left corner of the grid
        self.grid_offset_x = image_center_x - (total_grid_size / 2)
        self.grid_offset_y = image_center_y - (total_grid_size / 2)
    
    def scale_background_image(self, x_scale_factor, y_scale_factor=None):
        """Scale the background image by the given factors (1.0 = 100%)"""
        if not self.original_background_image or self.original_background_image.isNull():
            return
        
        # If only one scale factor provided, use it for both dimensions (backward compatibility)
        if y_scale_factor is None:
            y_scale_factor = x_scale_factor
        
        # Store current scales
        self.current_x_scale = x_scale_factor
        self.current_y_scale = y_scale_factor
        
        # Calculate new dimensions
        original_width = self.original_background_image.width()
        original_height = self.original_background_image.height()
        new_width = int(original_width * x_scale_factor)
        new_height = int(original_height * y_scale_factor)
        
        # Scale the image from the original
        self.background_image = self.original_background_image.scaled(
            new_width, new_height,
            Qt.IgnoreAspectRatio,  # Allow independent X/Y scaling
            Qt.SmoothTransformation
        )
        
        # Re-center the grid on the scaled image
        self.center_grid_on_image()
        
        # Trigger repaint
        self.update()
    
    def toggle_polygon_mode(self):
        """Toggle polygon drawing mode on/off"""
        self.polygon_mode = not self.polygon_mode
        
        if self.polygon_mode:
            # Entering polygon mode - exit eraser mode if active
            if self.eraser_mode:
                self.eraser_mode = False
                
                # Update eraser checkbox to reflect the change
                parent = self.parent()
                while parent:
                    for child in parent.findChildren(QCheckBox):
                        if child.text() == "Eraser Mode" and hasattr(child, 'setChecked'):
                            child.blockSignals(True)
                            child.setChecked(False)
                            child.blockSignals(False)
                            break
                    parent = parent.parent()
            
            self.polygon_points = []  # Reset points
            self.setCursor(Qt.BlankCursor)  # Hide cursor, we'll draw our own
            self.cursor_timer.start(50)  # Start cursor updates
        else:
            # Exiting polygon mode
            self.setCursor(Qt.ArrowCursor)  # Restore normal cursor
            self.polygon_points = []  # Clear any points
            self.cursor_timer.stop()  # Stop cursor updates
        
        self.update()  # Refresh display
    
    def add_polygon_point(self, screen_x, screen_y):
        """Add a point to the current polygon being drawn"""
        if not self.polygon_mode:
            return
        
        # Convert screen coordinates to world coordinates for storage
        world_x, world_y = self.screen_to_world(screen_x, screen_y)
        self.polygon_points.append((world_x, world_y))
        self.update()  # Refresh to show new point
    
    def finish_polygon(self):
        """Finish the current polygon if we have enough points"""
        if len(self.polygon_points) >= 3:
            # Create only a single polygon
            self.create_single_polygon()
        # If not enough points, keep them - user might want to add more
    
    def create_single_polygon(self):
        """Create a single polygon and optionally its duplicates"""
        if len(self.polygon_points) < 3:
            return

        # Assign group ID for this set of polygons
        current_group_id = self.next_group_id
        self.next_group_id += 1

        # Create original polygon with transparent fill and black frame
        original_polygon = {
            'points': list(self.polygon_points),  # Copy the points
            'color': QColor(0, 0, 0, 0),  # Transparent fill
            'frame_color': QColor(0, 0, 0, 255),  # Black frame
            'group_id': current_group_id  # Group ID for linking with copies
        }
        
        # Add original polygon
        self.polygons.append(original_polygon)
        
        # If duplicate mode is enabled, create 8 copies with offsets and colored frames
        if self.duplicate_mode:
            box_size = self.grid_size
            
            # Define the 8 offsets and corresponding frame colors
            offsets_and_colors = [
                ((-box_size, -box_size), QColor(255, 0, 0, 255)),    # 1st copy - Red frame
                ((-box_size, 0), QColor(0, 0, 255, 255)),            # 2nd copy - Blue frame
                ((-box_size, box_size), QColor(144, 238, 144, 255)), # 3rd copy - Light green frame
                ((0, -box_size), QColor(128, 0, 128, 255)),          # 4th copy - Purple frame
                ((0, box_size), QColor(255, 255, 0, 255)),           # 5th copy - Yellow frame
                ((box_size, -box_size), QColor(255, 192, 203, 255)), # 6th copy - Pink frame
                ((box_size, 0), QColor(128, 128, 128, 255)),         # 7th copy - Gray frame
                ((box_size, box_size), QColor(173, 216, 230, 255))   # 8th copy - Light blue frame
            ]
            
            # Create each duplicate with same group ID
            for (offset_x, offset_y), frame_color in offsets_and_colors:
                duplicate_points = []
                for point in self.polygon_points:
                    new_x = point[0] + offset_x
                    new_y = point[1] + offset_y
                    duplicate_points.append((new_x, new_y))
                
                duplicate_polygon = {
                    'points': duplicate_points,
                    'color': QColor(0, 0, 0, 0),  # Transparent fill
                    'frame_color': frame_color,   # Colored frame
                    'group_id': current_group_id  # Same group ID as original
                }
                
                self.polygons.append(duplicate_polygon)
        
        # Clear current points
        self.polygon_points = []
        self.update()  # Refresh display
    

    

    
    def get_average_color_from_background(self, world_points):
        """Get average color from background image at polygon area"""
        if not self.background_image or self.background_image.isNull():
            return QColor(128, 128, 128, 255)  # Default gray, fully opaque if no image
        
        try:
            # Convert QPixmap to QImage for pixel access
            background_image = self.background_image.toImage()
            
            # Convert world coordinates to image coordinates
            image_points = []
            for world_x, world_y in world_points:
                # Account for image offset
                image_x = world_x - self.image_offset_x
                image_y = world_y - self.image_offset_y
                image_points.append((int(image_x), int(image_y)))
            
            # Find bounding box of the polygon
            if not image_points:
                return QColor(128, 128, 128, 100)
            
            min_x = max(0, min(x for x, y in image_points))
            max_x = min(background_image.width() - 1, max(x for x, y in image_points))
            min_y = max(0, min(y for x, y in image_points))
            max_y = min(background_image.height() - 1, max(y for x, y in image_points))
            
            # Sample pixels within the polygon bounding box
            red_sum = green_sum = blue_sum = pixel_count = 0
            
            for y in range(min_y, max_y + 1):
                for x in range(min_x, max_x + 1):
                    # Simple point-in-polygon test using the bounding box
                    if self.point_in_polygon(x, y, image_points):
                        pixel = background_image.pixel(x, y)
                        red_sum += (pixel >> 16) & 0xFF
                        green_sum += (pixel >> 8) & 0xFF
                        blue_sum += pixel & 0xFF
                        pixel_count += 1
            
            if pixel_count > 0:
                # Calculate average color
                avg_red = red_sum // pixel_count
                avg_green = green_sum // pixel_count
                avg_blue = blue_sum // pixel_count
                return QColor(avg_red, avg_green, avg_blue, 255)  # Fully opaque
            else:
                return QColor(128, 128, 128, 255)  # Default gray, fully opaque
                
        except Exception as e:
            print(f"Error sampling background color: {e}")
            return QColor(128, 128, 128, 255)  # Default gray, fully opaque on error
    
    def point_in_polygon(self, x, y, polygon_points):
        """Simple point-in-polygon test using ray casting algorithm"""
        if len(polygon_points) < 3:
            return False
        
        inside = False
        j = len(polygon_points) - 1
        
        for i in range(len(polygon_points)):
            xi, yi = polygon_points[i]
            xj, yj = polygon_points[j]
            
            if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / (yj - yi) + xi):
                inside = not inside
            j = i
        
        return inside
    
    def mousePressEvent(self, event):
        """Handle mouse press events"""
        # Ensure canvas has focus for keyboard events
        self.setFocus()
        
        if event.button() == Qt.LeftButton and self.polygon_mode:
            # In polygon mode, left click adds point to polygon
            self.add_polygon_point(event.x(), event.y())
        elif event.button() == Qt.RightButton and self.polygon_mode:
            # Right click finishes the polygon
            self.finish_polygon()
        elif event.button() == Qt.LeftButton and not self.polygon_mode:
            # Check for eraser mode first
            if self.eraser_mode:
                world_x, world_y = self.screen_to_world(event.x(), event.y())
                self.erase_polygon_at_point(world_x, world_y)
                self.is_erasing = True  # Start erasing mode for drag
                return
            
            # Check for image drag handle click
            if self.is_point_in_image_drag_handle(event.x(), event.y()):
                # Start dragging image
                self.is_dragging_image = True
                self.image_drag_start_offset_x = self.image_offset_x
                self.image_drag_start_offset_y = self.image_offset_y
                self.last_pan_point = event.pos()
                self.setCursor(Qt.ClosedHandCursor)
                return
            
            # Check for grid drag handle click
            elif self.is_point_in_grid_drag_handle(event.x(), event.y()):
                # Start dragging grid
                self.grid_dragging = True
                self.grid_drag_start = event.pos()
                world_x, world_y = self.screen_to_world(event.x(), event.y())
                self.grid_drag_world_start = (world_x, world_y)
                self.setCursor(Qt.ClosedHandCursor)
                return
            
            # In selection mode, check for control point clicks
            control_point_index = self.find_control_point_at_screen_pos(event.x(), event.y())
            
            if control_point_index >= 0:
                # Start dragging control point
                self.selected_control_point = control_point_index
                self.is_dragging_control_point = True
                self.setCursor(Qt.ClosedHandCursor)
                self.update()
            else:
                # Check for polygon selection
                world_x, world_y = self.screen_to_world(event.x(), event.y())
                self.select_polygon_at_point(world_x, world_y)
        elif event.button() == Qt.MiddleButton:
            # Start panning
            self.is_panning = True
            self.last_pan_point = event.pos()
            self.setCursor(Qt.ClosedHandCursor)
    
    def mouseMoveEvent(self, event):
        """Handle mouse move events"""
        if self.is_erasing:
            # Continue erasing while dragging
            world_x, world_y = self.screen_to_world(event.x(), event.y())
            self.erase_polygon_at_point(world_x, world_y)
        elif self.is_dragging_image:
            # Drag image by converting screen movement to world offset
            if self.last_pan_point:
                delta = event.pos() - self.last_pan_point
                # Convert screen delta to world delta (accounting for zoom)
                world_delta_x = delta.x() / self.zoom_factor
                world_delta_y = delta.y() / self.zoom_factor
                
                # Update image offset
                self.image_offset_x += world_delta_x
                self.image_offset_y += world_delta_y
                self.last_pan_point = event.pos()
                self.update()
        elif self.grid_dragging and self.grid_drag_start:
            # Drag grid by updating offset
            delta = event.pos() - self.grid_drag_start
            # Convert screen delta to world delta (accounting for zoom)
            world_delta_x = delta.x() / self.zoom_factor
            world_delta_y = delta.y() / self.zoom_factor
            
            # Calculate new grid position
            start_world_x, start_world_y = self.grid_drag_world_start
            new_world_x = start_world_x + world_delta_x
            new_world_y = start_world_y + world_delta_y
            
            # Update grid offset to align with new position
            self.grid_offset_x = new_world_x
            self.grid_offset_y = new_world_y
            self.update()
            
        elif self.is_dragging_control_point and self.selected_control_point >= 0:
            # Drag control point to reshape polygon and optionally its group
            world_x, world_y = self.screen_to_world(event.x(), event.y())
            
            # Update the control point position of the selected polygon and its group
            if (self.selected_polygon_index >= 0 and 
                self.selected_polygon_index < len(self.polygons)):
                
                selected_polygon = self.polygons[self.selected_polygon_index]
                group_id = selected_polygon.get('group_id')
                selected_points = selected_polygon['points']
                
                if self.selected_control_point < len(selected_points):
                    # During dragging, only update the selected polygon
                    selected_points[self.selected_control_point] = (world_x, world_y)
                    self.update()
                    
                    self.update()
                    
        elif self.is_panning and self.last_pan_point:
            # Update pan offset
            delta = event.pos() - self.last_pan_point
            self.pan_offset_x += delta.x()
            self.pan_offset_y += delta.y()
            self.last_pan_point = event.pos()
            self.update()
        elif self.polygon_mode:
            # Update cursor position for polygon mode
            self.update()
        else:
            # Check if hovering over drag handles and update cursor
            if (not self.is_dragging_control_point and 
                not self.is_panning):
                
                if (self.background_image and 
                      self.is_point_in_image_drag_handle(event.x(), event.y())):
                    self.setCursor(Qt.OpenHandCursor)
                elif self.is_point_in_grid_drag_handle(event.x(), event.y()):
                    self.setCursor(Qt.OpenHandCursor)
                elif not self.polygon_mode and not self.eraser_mode:
                    self.setCursor(Qt.ArrowCursor)
                elif self.eraser_mode and not self.polygon_mode:
                    self.setCursor(Qt.PointingHandCursor)
    
    def mouseReleaseEvent(self, event):
        """Handle mouse release events"""
        if self.is_erasing:
            # Stop erasing
            self.is_erasing = False
        elif self.is_dragging_control_point:
            # Update all copies when control point dragging is complete
            if (self.duplicate_mode and self.selected_polygon_index >= 0 and 
                self.selected_polygon_index < len(self.polygons)):
                
                selected_polygon = self.polygons[self.selected_polygon_index]
                group_id = selected_polygon.get('group_id')
                
                if group_id is not None:
                    self.update_group_control_points_after_drag(group_id)
            
            # Stop dragging control point
            self.is_dragging_control_point = False
            self.selected_control_point = -1
            self.setCursor(Qt.ArrowCursor)
        elif self.is_dragging_image:
            self.is_dragging_image = False
            self.last_pan_point = None
            self.setCursor(Qt.ArrowCursor)
        elif self.grid_dragging:
            # Stop dragging grid
            self.grid_dragging = False
            self.grid_drag_start = None
            self.grid_drag_world_start = None
            self.setCursor(Qt.ArrowCursor)
        elif self.is_panning:
            self.is_panning = False
            self.last_pan_point = None
            self.setCursor(Qt.ArrowCursor if not self.polygon_mode else Qt.BlankCursor)
    
    def update_group_control_points_after_drag(self, group_id):
        """Update control points of all copies in the group based on the original polygon's new position"""
        if not self.duplicate_mode or group_id is None:
            return
            
        # Find the original polygon and all copies in the group
        group_polygons = [p for p in self.polygons if p.get('group_id') == group_id]
        if len(group_polygons) < 2:  # Need at least original + 1 copy
            return
            
        # Find the original polygon (the one with black frame)
        original_polygon = None
        for polygon in group_polygons:
            frame_color = polygon.get('frame_color', QColor(0, 0, 0, 255))
            if (frame_color.red() == 0 and frame_color.green() == 0 and 
                frame_color.blue() == 0 and frame_color.alpha() == 255):
                original_polygon = polygon
                break
                
        if not original_polygon or self.selected_control_point < 0:
            return
            
        # Get the new position of the moved control point from the original
        if self.selected_control_point >= len(original_polygon['points']):
            return
            
        original_new_point = original_polygon['points'][self.selected_control_point]
        
        # Define the same offsets used during creation
        box_size = self.grid_size
        offsets = [
            (-box_size, -box_size),  # 1st copy - Red frame
            (-box_size, 0),          # 2nd copy - Blue frame
            (-box_size, box_size),   # 3rd copy - Light green frame
            (0, -box_size),          # 4th copy - Purple frame
            (0, box_size),           # 5th copy - Yellow frame
            (box_size, -box_size),   # 6th copy - Pink frame
            (box_size, 0),           # 7th copy - Gray frame
            (box_size, box_size)     # 8th copy - Light blue frame
        ]
        
        # Update each copy's control point based on the offset from original
        copy_index = 0
        for polygon in group_polygons:
            if polygon is original_polygon:
                continue  # Skip the original polygon
                
            if copy_index < len(offsets) and self.selected_control_point < len(polygon['points']):
                offset_x, offset_y = offsets[copy_index]
                new_x = original_new_point[0] + offset_x
                new_y = original_new_point[1] + offset_y
                polygon['points'][self.selected_control_point] = (new_x, new_y)
                
            copy_index += 1
        
        self.update()  # Refresh display

    def wheelEvent(self, event):
        """Handle mouse wheel events for zooming"""
        # Get mouse position before zoom
        mouse_pos = event.pos()
        old_world_x, old_world_y = self.screen_to_world(mouse_pos.x(), mouse_pos.y())
        
        # Update zoom factor
        zoom_in = event.angleDelta().y() > 0
        zoom_factor = 1.25 if zoom_in else 0.8
        
        # Limit zoom range
        new_zoom = self.zoom_factor * zoom_factor
        if 0.1 <= new_zoom <= 10.0:
            self.zoom_factor = new_zoom
            
            # Adjust pan offset to keep mouse position fixed
            new_screen_x, new_screen_y = self.world_to_screen(old_world_x, old_world_y)
            self.pan_offset_x += mouse_pos.x() - new_screen_x
            self.pan_offset_y += mouse_pos.y() - new_screen_y
            
            self.update()
    
    def keyPressEvent(self, event):
        """Handle key press events"""
        if event.key() == Qt.Key_Escape:
            # Escape key releases polygon mode
            if self.polygon_mode:
                self.polygon_mode = False
                self.polygon_points = []  # Clear any in-progress polygon
                self.setCursor(Qt.ArrowCursor)
                self.cursor_timer.stop()
                self.update()
                
                # Find and update the checkbox - look for it in the widget hierarchy
                parent = self.parent()
                while parent:
                    # Look for SidePanel widgets in the parent's children
                    for child in parent.findChildren(QCheckBox):
                        if child.text() == "Polygon" and hasattr(child, 'setChecked'):
                            # Block signals to prevent triggering toggle_polygon_mode again
                            child.blockSignals(True)
                            child.setChecked(False)
                            child.blockSignals(False)
                            break
                    parent = parent.parent()
                    
        elif event.key() == Qt.Key_P:
            # P key toggles polygon mode
            self.toggle_polygon_mode()
            
            # Find and update the checkbox - look for it in the widget hierarchy
            parent = self.parent()
            while parent:
                # Look for SidePanel widgets in the parent's children
                for child in parent.findChildren(QCheckBox):
                    if child.text() == "Polygon" and hasattr(child, 'setChecked'):
                        # Block signals to prevent triggering toggle_polygon_mode again
                        child.blockSignals(True)
                        child.setChecked(self.polygon_mode)
                        child.blockSignals(False)
                        break
                parent = parent.parent()
                
        elif event.key() == Qt.Key_E:
            # E key toggles eraser mode
            self.set_eraser_mode(not self.eraser_mode)
            
            # Find and update the checkbox - look for it in the widget hierarchy
            parent = self.parent()
            while parent:
                # Look for SidePanel widgets in the parent's children
                for child in parent.findChildren(QCheckBox):
                    if child.text() == "Eraser Mode" and hasattr(child, 'setChecked'):
                        # Block signals to prevent triggering toggle_polygon_mode again
                        child.blockSignals(True)
                        child.setChecked(self.eraser_mode)
                        child.blockSignals(False)
                        break
                parent = parent.parent()
                    
        elif event.key() == Qt.Key_Delete:
            # Delete key removes selected polygon(s)
            if self.selected_polygon_indices:
                self.delete_selected_polygon()
        else:
            super().keyPressEvent(event)
    
    def delete_selected_polygon(self):
        """Delete the currently selected polygon and optionally all polygons in its group"""
        if self.selected_polygon_index < 0:
            return
        
        # Get the selected polygon and its group ID
        if 0 <= self.selected_polygon_index < len(self.polygons):
            selected_polygon = self.polygons[self.selected_polygon_index]
            group_id = selected_polygon.get('group_id')
            
            # Only apply group behavior if duplicate mode is currently enabled
            if self.duplicate_mode and group_id is not None:
                # Remove all polygons with the same group ID
                self.polygons = [p for p in self.polygons if p.get('group_id') != group_id]
            else:
                # If duplicate mode is off or no group ID, just remove the single polygon
                self.polygons.pop(self.selected_polygon_index)
        
        # Clear selection
        self.selected_polygon_index = -1
        self.update()
    
    def erase_polygon_at_point(self, world_x, world_y):
        """Erase the polygon or polygon group at the given point"""
        # Find polygon at point
        for i, polygon_data in enumerate(self.polygons):
            points = polygon_data['points']
            if self.point_in_polygon(world_x, world_y, points):
                # Get group ID of the polygon to erase
                group_id = polygon_data.get('group_id')
                
                # Only apply group behavior if duplicate mode is currently enabled
                if self.duplicate_mode and group_id is not None:
                    # Remove all polygons with the same group ID
                    self.polygons = [p for p in self.polygons if p.get('group_id') != group_id]
                else:
                    # If duplicate mode is off or no group ID, just remove the single polygon
                    self.polygons.pop(i)
                
                self.update()
                return True  # Successfully erased polygon(s)
        
        return False  # No polygon found at point
    
    def select_polygon_at_point(self, world_x, world_y):
        """Select a polygon at the given world coordinates"""
        self.selected_polygon_index = -1
        self.selected_polygon_indices = []
        
        # Check polygons in reverse order (last drawn first)
        for i in range(len(self.polygons) - 1, -1, -1):
            polygon_data = self.polygons[i]
            points = polygon_data['points']
            
            if self.point_in_polygon(world_x, world_y, points):
                self.selected_polygon_index = i
                break
        
        self.update()
    
    def point_in_polygon(self, x, y, polygon_points):
        """Check if a point is inside a polygon using ray casting algorithm"""
        if len(polygon_points) < 3:
            return False
        
        inside = False
        j = len(polygon_points) - 1
        
        for i in range(len(polygon_points)):
            xi, yi = polygon_points[i]
            xj, yj = polygon_points[j]
            
            if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / (yj - yi) + xi):
                inside = not inside
            j = i
        
        return inside
    
    def paintEvent(self, event):
        """Paint the canvas"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Fill canvas with white background
        painter.fillRect(self.rect(), QColor(255, 255, 255))
        
        # Apply zoom and pan transformation
        painter.translate(self.pan_offset_x, self.pan_offset_y)
        painter.scale(self.zoom_factor, self.zoom_factor)
        
        # Draw background image if available and enabled
        if self.background_image and not self.background_image.isNull() and self.show_image:
            # Draw image at original size with offset, transformations will handle zoom/pan
            painter.drawPixmap(int(self.image_offset_x), int(self.image_offset_y), self.background_image)
        
        # Reset transformation for UI elements
        painter.resetTransform()
        
        # Draw completed polygons (convert world coordinates to screen)
        for i, polygon_data in enumerate(self.polygons):
            points = polygon_data['points']
            color = polygon_data['color']
            frame_color = polygon_data.get('frame_color', QColor(0, 0, 0))  # Default to black if no frame_color
            
            if len(points) >= 3:
                # Convert world coordinates to screen coordinates
                screen_points = []
                for world_x, world_y in points:
                    screen_x, screen_y = self.world_to_screen(world_x, world_y)
                    screen_points.append(QPoint(int(screen_x), int(screen_y)))
                
                qpolygon = QPolygon(screen_points)
                
                # Highlight selected polygon
                if i == self.selected_polygon_index:
                    # Draw thicker red border for selected polygon
                    painter.setPen(QPen(QColor(255, 0, 0), 3))  # Red thick border
                else:
                    # Use the polygon's frame color
                    painter.setPen(QPen(frame_color, 2))  # Use frame color with thickness 2
                
                painter.setBrush(QBrush(color))
                painter.drawPolygon(qpolygon)
        
        # Draw control points for the selected polygon
        if self.selected_polygon_index >= 0:
            self.draw_control_points(painter)
        
        # Draw grid if enabled
        if self.show_grid:
            self.draw_grid(painter)
        
        # Draw polygon cursor and current points if in polygon mode
        if self.polygon_mode:
            # Get current mouse position relative to this widget
            cursor_pos = self.mapFromGlobal(QCursor.pos())
            if self.rect().contains(cursor_pos):
                # Draw square cursor
                painter.setPen(QPen(QColor(0, 255, 0), 2))  # Green square
                painter.setBrush(QBrush(Qt.NoBrush))  # No fill
                half_size = self.polygon_cursor_size // 2
                painter.drawRect(cursor_pos.x() - half_size, 
                               cursor_pos.y() - half_size,
                               self.polygon_cursor_size, 
                               self.polygon_cursor_size)
            
            # Draw current polygon points (convert world to screen coordinates)
            if self.polygon_points:
                painter.setPen(QPen(QColor(0, 255, 0), 3))  # Green points
                painter.setBrush(QBrush(QColor(0, 255, 0)))  # Green fill
                
                # Convert world coordinates to screen coordinates for display
                screen_points = []
                for world_x, world_y in self.polygon_points:
                    screen_x, screen_y = self.world_to_screen(world_x, world_y)
                    screen_points.append((screen_x, screen_y))
                
                # Draw points
                for i, (screen_x, screen_y) in enumerate(screen_points):
                    painter.drawEllipse(int(screen_x - 3), int(screen_y - 3), 6, 6)
                    
                    # Draw point number
                    painter.setPen(QPen(QColor(255, 255, 255), 1))
                    painter.setFont(QFont('Arial', 8, QFont.Bold))
                    painter.drawText(int(screen_x + 5), int(screen_y - 5), str(i + 1))
                    painter.setPen(QPen(QColor(0, 255, 0), 3))  # Reset pen for next point
                
                # Draw lines connecting the points
                if len(screen_points) > 1:
                    painter.setPen(QPen(QColor(0, 255, 0), 2))
                    for i in range(len(screen_points) - 1):
                        x1, y1 = screen_points[i]
                        x2, y2 = screen_points[i + 1]
                        painter.drawLine(int(x1), int(y1), int(x2), int(y2))
    
    def draw_control_points(self, painter):
        """Draw control points for the selected polygon"""
        if self.selected_polygon_index < 0 or self.selected_polygon_index >= len(self.polygons):
            return
        
        # Draw control points for the selected polygon
        polygon_data = self.polygons[self.selected_polygon_index]
        points = polygon_data['points']
        
        # Draw control points as yellow dots with blue outline
        for i, (world_x, world_y) in enumerate(points):
            # Convert world coordinates to screen coordinates
            screen_x, screen_y = self.world_to_screen(world_x, world_y)
            
            # Highlight selected control point
            if i == self.selected_control_point:
                painter.setPen(QPen(QColor(255, 0, 0), 3))  # Red outline for selected
                painter.setBrush(QBrush(QColor(255, 255, 0)))  # Yellow fill
            else:
                painter.setPen(QPen(QColor(0, 0, 255), 2))  # Blue outline
                painter.setBrush(QBrush(QColor(255, 255, 0)))  # Yellow fill
            
            # Draw the control point circle
            half_size = self.control_point_size // 2
            painter.drawEllipse(int(screen_x - half_size), int(screen_y - half_size),
                              self.control_point_size, self.control_point_size)

    def draw_grid(self, painter):
        """Draw the 3x3 grid overlay with draggable handle that scales with zoom"""
        
        # Calculate grid position and size in world coordinates
        # grid_size is the size of each individual box/cell
        cell_size_world = self.grid_size
        total_grid_size_world = cell_size_world * 3  # 3 boxes = total grid size
        grid_x_world = self.grid_offset_x
        grid_y_world = self.grid_offset_y
        
        # Convert grid corners to screen coordinates
        grid_x_screen, grid_y_screen = self.world_to_screen(grid_x_world, grid_y_world)
        grid_end_x_screen, grid_end_y_screen = self.world_to_screen(
            grid_x_world + total_grid_size_world, grid_y_world + total_grid_size_world)
        
        # Calculate screen cell size
        cell_size_screen = (grid_end_x_screen - grid_x_screen) / 3
        
        # Draw grid lines
        painter.setPen(QPen(QColor(0, 0, 255), 2))  # Blue grid lines
        
        # Draw 3x3 grid (4 lines in each direction to create 3 boxes)
        for i in range(4):
            # Vertical lines
            x_screen = grid_x_screen + (i * cell_size_screen)
            painter.drawLine(int(x_screen), int(grid_y_screen), 
                           int(x_screen), int(grid_end_y_screen))
            
            # Horizontal lines
            y_screen = grid_y_screen + (i * cell_size_screen)
            painter.drawLine(int(grid_x_screen), int(y_screen), 
                           int(grid_end_x_screen), int(y_screen))
        
        # Draw column numbers (1-3) at the top of each column
        painter.setPen(QPen(QColor(0, 0, 255), 1))
        font = QFont()
        font.setPixelSize(max(12, int(cell_size_screen / 8)))  # Scale font with grid
        painter.setFont(font)
        
        for col in range(3):
            x_center = grid_x_screen + (col + 0.5) * cell_size_screen
            y_pos = grid_y_screen - 10  # Above the grid
            painter.drawText(int(x_center - 5), int(y_pos), str(col + 1))
        
        # Draw row numbers (1-3) at the left of each row
        for row in range(3):
            x_pos = grid_x_screen - 15  # Left of the grid
            y_center = grid_y_screen + (row + 0.5) * cell_size_screen
            painter.drawText(int(x_pos), int(y_center + 5), str(row + 1))
        
        # Draw drag handle (small square at top-left corner of grid)
        handle_size = max(8, int(cell_size_screen / 10))
        handle_x = grid_x_screen - handle_size
        handle_y = grid_y_screen - handle_size
        
        painter.setPen(QPen(QColor(255, 0, 0), 2))  # Red handle
        painter.setBrush(QBrush(QColor(255, 255, 255)))  # White fill
        painter.drawRect(int(handle_x), int(handle_y), handle_size, handle_size)
    
    def is_point_in_grid_drag_handle(self, screen_x, screen_y):
        """Check if a screen point is inside the grid drag handle"""
        if not self.show_grid:
            return False
            
        # Calculate grid position and handle position
        cell_size_world = self.grid_size
        total_grid_size_world = cell_size_world * 3
        grid_x_world = self.grid_offset_x
        grid_y_world = self.grid_offset_y
        
        # Convert to screen coordinates
        grid_x_screen, grid_y_screen = self.world_to_screen(grid_x_world, grid_y_world)
        grid_end_x_screen, grid_end_y_screen = self.world_to_screen(
            grid_x_world + total_grid_size_world, grid_y_world + total_grid_size_world)
        
        cell_size_screen = (grid_end_x_screen - grid_x_screen) / 3
        handle_size = max(8, int(cell_size_screen / 10))
        handle_x = grid_x_screen - handle_size
        handle_y = grid_y_screen - handle_size
        
        # Check if point is within handle rectangle
        return (handle_x <= screen_x <= handle_x + handle_size and
                handle_y <= screen_y <= handle_y + handle_size)

    def find_control_point_at_screen_pos(self, screen_x, screen_y):
        """Find which control point is at the given screen position"""
        if self.selected_polygon_index < 0 or self.selected_polygon_index >= len(self.polygons):
            return -1
            
        polygon_data = self.polygons[self.selected_polygon_index]
        points = polygon_data['points']
        
        for i, (world_x, world_y) in enumerate(points):
            # Convert world coordinates to screen coordinates
            point_screen_x, point_screen_y = self.world_to_screen(world_x, world_y)
            
            # Check if click is within control point circle
            distance = ((screen_x - point_screen_x)**2 + (screen_y - point_screen_y)**2)**0.5
            if distance <= self.control_point_size:
                return i
                
        return -1


class SidePanel(QFrame):
    """Side panel widget"""
    
    def __init__(self, title, canvas=None):
        super().__init__()
        self.setFrameStyle(QFrame.StyledPanel)
        self.setMinimumWidth(200)
        self.setMaximumWidth(250)
        self.setStyleSheet("background-color: #f0f0f0;")
        self.canvas = canvas
        
        # Create layout for the panel
        layout = QVBoxLayout()
        
        # Add buttons for right panel
        if title == "Right Panel" and canvas:
            load_bg_button = QPushButton("Load Background")
            load_bg_button.clicked.connect(self.load_background)
            layout.addWidget(load_bg_button)
            
            # Add polygon checkbox
            self.polygon_checkbox = QCheckBox("Polygon")
            self.polygon_checkbox.toggled.connect(self.on_polygon_toggled)
            layout.addWidget(self.polygon_checkbox)
            
            # Add eraser mode checkbox
            self.eraser_checkbox = QCheckBox("Eraser Mode")
            self.eraser_checkbox.toggled.connect(self.on_eraser_toggled)
            layout.addWidget(self.eraser_checkbox)
            
            # Add duplicate mode checkbox
            self.duplicate_checkbox = QCheckBox("Duplicate")
            self.duplicate_checkbox.toggled.connect(self.on_duplicate_toggled)
            layout.addWidget(self.duplicate_checkbox)
            
            # Add show image checkbox
            self.show_image_checkbox = QCheckBox("Show Image")
            self.show_image_checkbox.setChecked(True)  # Checked by default
            self.show_image_checkbox.toggled.connect(self.on_show_image_toggled)
            layout.addWidget(self.show_image_checkbox)
            
            # X scale input
            x_scale_label = QLabel('X Scale (%):')
            layout.addWidget(x_scale_label)
            
            self.x_scale_input = QLineEdit()
            self.x_scale_input.setText('100')
            self.x_scale_input.setPlaceholderText('Enter X scale percentage (e.g., 100)')
            self.x_scale_input.textChanged.connect(self.on_scale_changed)
            layout.addWidget(self.x_scale_input)
            
            # Y scale input
            y_scale_label = QLabel('Y Scale (%):')
            layout.addWidget(y_scale_label)
            
            self.y_scale_input = QLineEdit()
            self.y_scale_input.setText('100')
            self.y_scale_input.setPlaceholderText('Enter Y scale percentage (e.g., 100)')
            self.y_scale_input.textChanged.connect(self.on_scale_changed)
            layout.addWidget(self.y_scale_input)
            
            # Add grid checkbox
            self.grid_checkbox = QCheckBox("Show Grid")
            self.grid_checkbox.setChecked(False)  # Unchecked by default
            self.grid_checkbox.toggled.connect(self.on_grid_toggled)
            layout.addWidget(self.grid_checkbox)
            
            # Grid size input
            grid_size_label = QLabel('Box Size:')
            layout.addWidget(grid_size_label)
            
            self.grid_size_input = QLineEdit()
            self.grid_size_input.setText('300')
            self.grid_size_input.setPlaceholderText('Enter box size (e.g., 300)')
            self.grid_size_input.textChanged.connect(self.on_grid_size_changed)
            layout.addWidget(self.grid_size_input)
            
            # Add save and load array buttons
            save_array_button = QPushButton("Save Array")
            save_array_button.clicked.connect(self.save_array)
            layout.addWidget(save_array_button)
            
            load_array_button = QPushButton("Load Array")
            load_array_button.clicked.connect(self.load_array)
            layout.addWidget(load_array_button)
        
        # Add stretch to push content to top
        layout.addStretch()
        
        self.setLayout(layout)
    
    def load_background(self):
        """Load background image for canvas"""
        if not self.canvas:
            return
            
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Load Background Image",
            "",
            "Image files (*.png *.jpg *.jpeg *.bmp *.tiff *.gif);;All files (*.*)"
        )
        
        if file_path:
            # Load image at original size without popup
            self.canvas.set_background_image(file_path)
            # Reset scale inputs to 100%
            if hasattr(self, 'x_scale_input'):
                self.x_scale_input.blockSignals(True)  # Prevent triggering scale change
                self.x_scale_input.setText('100')
                self.x_scale_input.blockSignals(False)
                
            if hasattr(self, 'y_scale_input'):
                self.y_scale_input.blockSignals(True)  # Prevent triggering scale change
                self.y_scale_input.setText('100')
                self.y_scale_input.blockSignals(False)
    
    def on_polygon_toggled(self, checked):
        """Handle polygon checkbox toggle"""
        if self.canvas:
            self.canvas.toggle_polygon_mode()
    
    def on_eraser_toggled(self, checked):
        """Handle eraser mode checkbox toggle"""
        if self.canvas:
            self.canvas.set_eraser_mode(checked)
    
    def on_duplicate_toggled(self, checked):
        """Handle duplicate mode checkbox toggle"""
        if self.canvas:
            self.canvas.duplicate_mode = checked
    
    def on_show_image_toggled(self, checked):
        """Handle show image checkbox toggle"""
        if self.canvas:
            self.canvas.set_image_visible(checked)
    
    def on_grid_toggled(self, checked):
        """Handle grid checkbox toggle"""
        if self.canvas:
            self.canvas.show_grid = checked
            self.canvas.update()
    
    def on_grid_size_changed(self):
        """Handle grid size changes"""
        try:
            text = self.grid_size_input.text().strip()
            if not text:
                return  # Don't change anything for empty input
                
            grid_size = int(text)
            grid_size = max(10, min(2000, grid_size))  # Clamp between 10 and 2000
            
            if self.canvas:
                self.canvas.grid_size = grid_size
                # Re-center grid on image if there's an image loaded
                self.canvas.center_grid_on_image()
                self.canvas.update()
        except ValueError:
            # Invalid input, ignore
            pass
    
    def on_scale_changed(self):
        """Handle X and Y scale changes"""
        try:
            x_text = self.x_scale_input.text().strip()
            y_text = self.y_scale_input.text().strip()
            
            if not x_text or not y_text:
                return  # Don't change anything for empty input
                
            x_scale_percentage = float(x_text)
            y_scale_percentage = float(y_text)
            
            # Clamp between 1% and 1000%
            x_scale_percentage = max(1, min(1000, x_scale_percentage))
            y_scale_percentage = max(1, min(1000, y_scale_percentage))
            
            if self.canvas:
                self.canvas.scale_background_image(x_scale_percentage / 100.0, y_scale_percentage / 100.0)
        except ValueError:
            # Invalid input, ignore
            pass
    
    def save_array(self):
        """Save polygons to CSV file compatible with mosaic_editor_pyqt"""
        if not self.canvas or not self.canvas.polygons:
            QMessageBox.warning(self, "Warning", "No polygons to save.")
            return
        
        # Open file dialog to choose save location
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Save Array as CSV",
            "",
            "CSV Files (*.csv);;All Files (*)"
        )
        
        if not filename:
            return  # User cancelled
        
        try:
            with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                
                # Write header with frame color support and group ID
                writer.writerow(['polygon_id', 'coordinates', 'color_r', 'color_g', 'color_b', 'color_a', 
                               'frame_r', 'frame_g', 'frame_b', 'frame_a', 'group_id'])
                
                # Write each polygon
                for i, polygon_data in enumerate(self.canvas.polygons):
                    points = polygon_data['points']
                    color = polygon_data['color']
                    frame_color = polygon_data.get('frame_color', QColor(0, 0, 0, 255))  # Default to black
                    group_id = polygon_data.get('group_id', '')  # Get group ID if available
                    
                    # Convert points to JSON string format (same as mosaic_editor_pyqt)
                    coords_json = json.dumps([[float(x), float(y)] for x, y in points])
                    
                    # Extract RGBA values (convert from QColor to 0-1 range)
                    r = color.red() / 255.0
                    g = color.green() / 255.0
                    b = color.blue() / 255.0
                    a = color.alpha() / 255.0
                    
                    # Extract frame color RGBA values
                    fr = frame_color.red() / 255.0
                    fg = frame_color.green() / 255.0
                    fb = frame_color.blue() / 255.0
                    fa = frame_color.alpha() / 255.0
                    
                    # Write row with group ID
                    writer.writerow([i, coords_json, r, g, b, a, fr, fg, fb, fa, group_id])
            
            QMessageBox.information(
                self, 
                "Success", 
                f"Saved {len(self.canvas.polygons)} polygons to {filename}"
            )
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save array: {str(e)}")
    
    def load_array(self):
        """Load polygons from CSV file compatible with mosaic_editor_pyqt"""
        if not self.canvas:
            return
            
        # Open file dialog to choose file
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Load Array from CSV",
            "",
            "CSV Files (*.csv);;All Files (*)"
        )
        
        if not filename:
            return  # User cancelled
        
        try:
            polygons = []
            
            with open(filename, 'r', newline='', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                for row_num, row in enumerate(reader, 1):
                    try:
                        # Parse coordinates - handle JSON array format
                        coords_str = row['coordinates'] if 'coordinates' in row else row.get('polygon_coords', '')
                        
                        # Remove quotes and parse as JSON
                        coords_str = coords_str.strip('"\'')
                        
                        try:
                            coord_list = json.loads(coords_str)
                            points = [(float(point[0]), float(point[1])) for point in coord_list]
                        except:
                            # Fallback to ast parsing for backward compatibility
                            import ast
                            coord_list = ast.literal_eval(coords_str)
                            points = [(float(point[0]), float(point[1])) for point in coord_list]
                        
                        if len(points) < 3:
                            continue
                        
                        # Parse color - handle separate R,G,B columns
                        if 'color_r' in row and 'color_g' in row and 'color_b' in row:
                            r = float(row['color_r'])
                            g = float(row['color_g'])
                            b = float(row['color_b'])
                            
                            # Check for alpha channel
                            if 'color_a' in row:
                                a = float(row['color_a'])
                                a = int(a * 255) if a <= 1.0 else int(a)
                            else:
                                a = 255  # Default to fully opaque
                            
                            # Convert from 0-1 range to 0-255
                            r = int(r * 255) if r <= 1.0 else int(r)
                            g = int(g * 255) if g <= 1.0 else int(g)
                            b = int(b * 255) if b <= 1.0 else int(b)
                            
                            color = QColor(r, g, b, a)
                        else:
                            # Default color if no color data
                            color = QColor(100, 100, 100)
                        
                        # Parse frame color if available
                        if 'frame_r' in row and 'frame_g' in row and 'frame_b' in row:
                            fr = float(row['frame_r'])
                            fg = float(row['frame_g'])
                            fb = float(row['frame_b'])
                            
                            # Check for frame alpha channel
                            if 'frame_a' in row:
                                fa = float(row['frame_a'])
                                fa = int(fa * 255) if fa <= 1.0 else int(fa)
                            else:
                                fa = 255  # Default to fully opaque
                            
                            # Convert from 0-1 range to 0-255
                            fr = int(fr * 255) if fr <= 1.0 else int(fr)
                            fg = int(fg * 255) if fg <= 1.0 else int(fg)
                            fb = int(fb * 255) if fb <= 1.0 else int(fb)
                            
                            frame_color = QColor(fr, fg, fb, fa)
                        else:
                            # Default frame color if no frame color data
                            frame_color = QColor(0, 0, 0, 255)  # Black frame
                        
                        # Parse group ID if available
                        group_id = None
                        if 'group_id' in row and row['group_id']:
                            try:
                                group_id = int(row['group_id'])
                            except:
                                group_id = None
                        
                        # Create polygon data structure
                        polygon_data = {
                            'points': points,
                            'color': color,
                            'frame_color': frame_color,
                            'group_id': group_id
                        }
                        polygons.append(polygon_data)
                        
                    except Exception as e:
                        print(f"Error parsing row {row_num}: {e}")
                        continue
            
            if polygons:
                # Clear existing polygons and load new ones
                self.canvas.polygons = polygons
                
                # Update next_group_id to avoid conflicts with loaded polygons
                max_group_id = 0
                for polygon in polygons:
                    group_id = polygon.get('group_id')
                    if group_id is not None and isinstance(group_id, int):
                        max_group_id = max(max_group_id, group_id)
                
                self.canvas.next_group_id = max_group_id + 1
                self.canvas.update()
                
                QMessageBox.information(
                    self, 
                    "Success", 
                    f"Loaded {len(polygons)} polygons from {filename}"
                )
            else:
                QMessageBox.warning(self, "Warning", "No valid polygons found in the file.")
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load array: {str(e)}")


class MandalaMosaicWindow(QMainWindow):
    """Main application window"""
    
    def __init__(self):
        super().__init__()
        self.initUI()
    
    def initUI(self):
        """Initialize the user interface"""
        self.setWindowTitle("Mandala Mosaic")
        self.setGeometry(100, 100, 1200, 800)
        
        # Create central widget and main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QHBoxLayout()
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        # Create left panel
        left_panel = SidePanel("Left Panel")
        main_layout.addWidget(left_panel)
        
        # Create central canvas
        canvas = Canvas()
        main_layout.addWidget(canvas, 1)  # Give canvas stretch factor of 1
        
        # Create right panel (with reference to canvas for background loading)
        right_panel = SidePanel("Right Panel", canvas)
        main_layout.addWidget(right_panel)
        
        central_widget.setLayout(main_layout)


def main():
    """Main application entry point"""
    app = QApplication(sys.argv)
    
    # Create and show the main window
    window = MandalaMosaicWindow()
    window.show()
    
    # Start the event loop
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
