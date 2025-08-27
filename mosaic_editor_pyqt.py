#!/usr/bin/env python3
"""
Mosaic Editor - Pure PyQt5 Implementation
A professional mosaic viewing and editing application using only PyQt5 for rendering.
"""

import sys
import csv
import json
import numpy as np
import cv2
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                           QHBoxLayout, QPushButton, QFileDialog, QLabel, 
                           QCheckBox, QScrollArea, QMessageBox,
                           QFrame, QSizePolicy, QLineEdit, QGridLayout)
from PyQt5.QtCore import Qt, QPointF, QRectF, QRect, pyqtSignal
from PyQt5.QtGui import QPainter, QPen, QBrush, QColor, QPolygonF, QFont, QWheelEvent, QTransform, QPixmap
from shapely.geometry import Polygon
import random


class ColorPaletteWidget(QWidget):
    """Widget that displays a color palette extracted from color_palette2.csv"""
    
    color_selected = pyqtSignal(QColor)  # Signal emitted when a color is selected
    
    def __init__(self, palette_file=None):
        super().__init__()
        self.colors = []
        self.selected_color = QColor(0, 0, 0)  # Default to black
        self.color_size = 20  # Size of each color square (20x20 pixels)
        self.selected_color_width = 40  # Width of selected color rectangle
        self.selected_color_height = 20  # Height of selected color rectangle
        self.palette_file = palette_file or 'color_palette2.csv'  # Default palette file
        self.setFixedHeight(60)  # Fixed height for the palette (adjusted for larger squares)
        self.setMinimumWidth(450)  # Increased slightly to accommodate selection rectangle next to palette
        self.load_palette_colors()
        
    def load_palette_colors(self):
        """Load colors from specified palette file (CSV or NPY format)"""
        import os
        import numpy as np
        
        # Try to load the specified palette file
        palette_path = os.path.join(os.path.dirname(__file__), self.palette_file)
        
        if self.palette_file.endswith('.npy'):
            # Load NPY file from color_collections folder
            npy_path = os.path.join(os.path.dirname(__file__), 'color_collections', self.palette_file)
            if os.path.exists(npy_path):
                try:
                    # Load numpy array of colors
                    color_array = np.load(npy_path)
                    self.colors = []
                    
                    # Convert numpy array to QColor objects
                    for color_rgb in color_array:
                        if len(color_rgb) >= 3:
                            # Assume RGB values are in 0-255 range
                            r, g, b = int(color_rgb[0]), int(color_rgb[1]), int(color_rgb[2])
                            color = QColor(r, g, b)
                            if color.isValid():
                                self.colors.append(color)
                    
                    if self.colors:
                        return  # Successfully loaded NPY palette
                except Exception as e:
                    print(f"Error loading NPY palette {self.palette_file}: {e}")
        
        # Try CSV format (fallback or default)
        if self.palette_file.endswith('.csv') or not self.colors:
            csv_path = os.path.join(os.path.dirname(__file__), 'color_palette2.csv')
            if os.path.exists(csv_path):
                try:
                    with open(csv_path, 'r', encoding='utf-8') as file:
                        lines = file.readlines()
                        
                    # Skip header line if it exists
                    start_line = 1 if lines and ('color' in lines[0].lower() or '#' not in lines[0]) else 0
                    
                    for line in lines[start_line:]:
                        line = line.strip()
                        if line and line.startswith('#') and len(line) == 7:
                            try:
                                color = QColor(line)
                                if color.isValid():
                                    self.colors.append(color)
                            except:
                                continue
                    
                    if self.colors:
                        return  # Successfully loaded CSV palette
                        
                except Exception as e:
                    print(f"Error loading CSV palette: {e}")
        
        # Load default colors if nothing else worked
        self.load_default_colors()
    
    def load_default_colors(self):
        """Load default colors if color_palette2.csv is not available"""
        default_colors = [
            '#FF0000', '#00FF00', '#0000FF', '#FFFF00', '#FF00FF', '#00FFFF',
            '#800000', '#008000', '#000080', '#808000', '#800080', '#008080',
            '#FFA500', '#FFC0CB', '#800080', '#A52A2A', '#D2691E', '#FF1493',
            '#32CD32', '#FF69B4', '#DC143C', '#00CED1', '#FF6347', '#4B0082'
        ]
        self.colors = [QColor(color) for color in default_colors]
    
    def change_palette(self, csv_file_path):
        """Change to a different CSV palette file and reload colors"""
        import os
        
        if not csv_file_path or not os.path.exists(csv_file_path):
            return False
            
        try:
            self.colors = []
            with open(csv_file_path, 'r', encoding='utf-8') as file:
                lines = file.readlines()
                
            # Skip header line if it exists
            start_line = 1 if lines and ('color' in lines[0].lower() or '#' not in lines[0]) else 0
            
            for line in lines[start_line:]:
                line = line.strip()
                if line and line.startswith('#') and len(line) == 7:
                    try:
                        color = QColor(line)
                        if color.isValid():
                            self.colors.append(color)
                    except:
                        continue
            
            if self.colors:
                self.update()  # Trigger repaint
                return True
            else:
                self.load_default_colors()
                return False
                
        except Exception as e:
            print(f"Error loading palette {csv_file_path}: {e}")
            self.load_default_colors()
            return False
    
    def paintEvent(self, event):
        """Paint the color palette and selected color rectangle"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Calculate layout with spacing for 20x20 squares
        margin = 5
        spacing = 2
        available_width = self.width() - 2 * margin
        colors_per_row = max(1, available_width // (self.color_size + spacing))
        
        x = margin
        y = margin
        last_x = x
        last_y = y
        
        # Draw color palette squares
        for i, color in enumerate(self.colors):
            # Draw color square (20x20 pixels)
            rect = QRectF(x, y, self.color_size, self.color_size)
            
            # Draw border (thicker if selected)
            if color == self.selected_color:
                painter.setPen(QPen(QColor(0, 0, 0), 3))
            else:
                painter.setPen(QPen(QColor(128, 128, 128), 1))
            
            painter.setBrush(QBrush(color))
            painter.drawRect(rect)
            
            # Store position for next placement
            last_x = x
            last_y = y
            
            # Move to next position
            x += self.color_size + spacing
            if (i + 1) % colors_per_row == 0:
                x = margin
                y += self.color_size + spacing
        
        # Draw selected color rectangle right next to the last color square
        selection_x = last_x + self.color_size + spacing + 5  # 5 pixels extra gap
        selection_y = last_y + (self.color_size - self.selected_color_height) // 2  # Center vertically with color squares
        selection_rect = QRectF(selection_x, selection_y, self.selected_color_width, self.selected_color_height)
        
        # Draw border for selected color rectangle
        painter.setPen(QPen(QColor(0, 0, 0), 2))
        painter.setBrush(QBrush(self.selected_color))
        painter.drawRect(selection_rect)
        
        # Add label below the selected color rectangle
        painter.setPen(QPen(QColor(0, 0, 0), 1))
        painter.setFont(QFont('Arial', 8))
        label_rect = QRectF(selection_x - 5, selection_y + self.selected_color_height + 2, 
                           self.selected_color_width + 10, 15)
        ###painter.drawText(label_rect, Qt.AlignCenter, f"Selected: {self.selected_color.name().upper()}")
    
    def mousePressEvent(self, event):
        """Handle mouse clicks to select colors"""
        if event.button() == Qt.LeftButton:
            # Calculate which color was clicked
            margin = 5
            spacing = 2
            available_width = self.width() - 2 * margin
            colors_per_row = max(1, available_width // (self.color_size + spacing))
            
            click_x = event.x() - margin
            click_y = event.y() - margin
            
            if click_x >= 0 and click_y >= 0:
                col = click_x // (self.color_size + spacing)
                row = click_y // (self.color_size + spacing)
                color_index = row * colors_per_row + col
                
                if 0 <= color_index < len(self.colors):
                    self.selected_color = self.colors[color_index]
                    self.color_selected.emit(self.selected_color)
                    self.update()  # Trigger repaint


class MosaicCanvas(QWidget):
    """Custom widget for displaying mosaic using pure PyQt5"""
    
    def __init__(self):
        super().__init__()
        self.polygons = []
        self.colors = []
        self.edge_colors = []  # Store edge/frame colors separately
        self.show_edges = True
        self.edge_width = 0.1  # Changed default from 1.0 to 0.1
        self.background_brightness = 0.9
        self.min_area = 30  # minimum area for small shapes
        self.transparent_shapes = False  # Whether to show shapes transparently
        self.background_image = None  # Background image pixmap
        self.background_image_path = None  # Path to background image
        self.background_offset_x = 0.0  # X offset for background image
        self.background_offset_y = 0.0  # Y offset for background image
        self.background_visible = True  # Whether background image is visible
        self.canvas_background_color = QColor(255, 255, 255)  # Default white canvas background
        
        # Eraser mode variables
        self.eraser_mode = False  # Whether eraser mode is active
        self.eraser_cursor = None  # Circle cursor for eraser mode
        self.eraser_radius = 5  # Radius of the eraser in screen pixels
        self.is_erasing = False  # Currently erasing shapes
        
        # Polygon drawing mode variables
        self.polygon_mode = False  # Whether polygon drawing mode is active
        self.polygon_points = []  # Points for the current polygon being drawn
        self.polygon_cursor_size = 10  # Size of the square cursor in pixels
        
        # Overlap check mode variables
        self.overlap_check_mode = False  # Whether overlap check mode is active
        self.overlap_highlights = []  # List of overlapping polygon pairs
        
        # Grid variables
        self.show_grid = False  # Whether to show the grid
        self.grid_size = 300  # Size of each individual grid box/cell in world coordinates
        self.grid_offset_x = 0  # Grid offset in world coordinates
        self.grid_offset_y = 0  # Grid offset in world coordinates
        self.grid_dragging = False  # Whether we're dragging the grid
        self.grid_drag_start = None  # Starting point for grid drag
        self.grid_drag_world_start = None  # Starting world coordinates for grid drag
        self.cut_tiles_applied = False  # Whether Cut Tiles has been applied (for grid box fill colors)
        
        # Zoom and pan variables
        self.scale_factor = 1.0
        self.offset_x = 0.0
        self.offset_y = 0.0
        self.last_pan_point = None
        self.is_panning = False
        
        # Shape dragging variables
        self.selected_polygon_index = -1  # Index of selected polygon
        self.is_dragging_shape = False
        self.last_drag_point = None
        
        # Contour display variables
        self.visible_polygons = []  # Store visible polygons for display
        self.drag_start_world_pos = None
        
        # Control point editing
        self.selected_control_point = -1  # Index of selected control point
        self.is_dragging_control_point = False
        self.control_point_size = 8  # Size of control point circles
        
        # Paint mode variables
        self.paint_mode = False
        self.is_painting = False  # Track if we're in paint drag mode
        self.last_painted_polygon = -1  # Track last painted polygon to avoid redundant paints
        self.selected_palette_color = QColor(0, 0, 0)  # Default to black
        
        # Original bounds for zoom-to-fit
        self.original_bounds = None
        
        # Performance optimization
        self.cached_polygons = []  # Cache transformed polygons
        self.cache_valid = False
        self.visible_indices = []  # Only draw visible polygons
        
        # View change callback
        self.view_changed = None
        
        # Set minimum size and enable mouse tracking
        self.setMinimumSize(800, 600)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.StrongFocus)  # Changed to StrongFocus for better key handling
        
        # Enable double buffering for smoother rendering
        self.setAttribute(Qt.WA_OpaquePaintEvent, True)
        
    def load_polygons_from_csv(self, filename):
        """Load polygons from CSV file"""
        try:
            polygons = []
            colors = []
            
            with open(filename, 'r', newline='') as csvfile:
                reader = csv.DictReader(csvfile)
                for row_num, row in enumerate(reader, 1):
                    try:
                        # Parse coordinates - handle JSON array format
                        coords_str = row['coordinates'] if 'coordinates' in row else row.get('polygon_coords', '')
                        
                        # Remove quotes and parse as JSON-like structure
                        coords_str = coords_str.strip('"\'')
                        
                        # Parse JSON-like coordinate array
                        try:
                            import ast
                            coord_list = ast.literal_eval(coords_str)
                            coords = [(float(point[0]), float(point[1])) for point in coord_list]
                        except:
                            # Fallback to manual parsing
                            coords_str = coords_str.strip('[]')
                            # Split by closing and opening brackets
                            coord_pairs = []
                            parts = coords_str.split('], [')
                            for part in parts:
                                part = part.strip('[]')
                                if ', ' in part:
                                    x_str, y_str = part.split(', ')
                                    try:
                                        x = float(x_str)
                                        y = float(y_str)
                                        coord_pairs.append((x, y))
                                    except ValueError:
                                        continue
                            coords = coord_pairs
                        
                        if len(coords) < 3:
                            continue
                        
                        # Create polygon
                        polygon = Polygon(coords)
                        if not polygon.is_valid:
                            continue
                        polygons.append(polygon)
                        
                        # Parse color - handle separate R,G,B columns or combined color column
                        if 'color_r' in row and 'color_g' in row and 'color_b' in row:
                            # Separate RGB columns (with optional alpha)
                            try:
                                r = float(row['color_r'])
                                g = float(row['color_g'])
                                b = float(row['color_b'])
                                
                                # Check for alpha channel (backward compatibility)
                                if 'color_a' in row:
                                    a = float(row['color_a'])
                                    a = int(a * 255) if a <= 1.0 else int(a)
                                else:
                                    a = 255  # Default to fully opaque if no alpha
                                
                                # Convert from 0-1 range to 0-255
                                r = int(r * 255) if r <= 1.0 else int(r)
                                g = int(g * 255) if g <= 1.0 else int(g)
                                b = int(b * 255) if b <= 1.0 else int(b)
                                
                                colors.append(QColor(r, g, b, a))
                            except ValueError as ve:
                                colors.append(QColor(128, 128, 128))  # Default gray
                        elif 'color' in row:
                            # Combined color column
                            color_str = row['color'].strip('()[]"\'')
                            
                            # Split color components
                            if ', ' in color_str:
                                color_parts = color_str.split(', ')
                            elif ',' in color_str:
                                color_parts = color_str.split(',')
                            else:
                                color_parts = color_str.split()
                            
                            if len(color_parts) >= 3:
                                try:
                                    r = float(color_parts[0].strip())
                                    g = float(color_parts[1].strip())
                                    b = float(color_parts[2].strip())
                                    
                                    # Handle both 0-1 and 0-255 ranges
                                    if r <= 1.0 and g <= 1.0 and b <= 1.0:
                                        r, g, b = int(r*255), int(g*255), int(b*255)
                                    else:
                                        r, g, b = int(r), int(g), int(b)
                                    
                                    colors.append(QColor(r, g, b))
                                except ValueError as ve:
                                    colors.append(QColor(128, 128, 128))  # Default gray
                            else:
                                colors.append(QColor(128, 128, 128))  # Default gray
                        else:
                            # No color information, use default
                            colors.append(QColor(128, 128, 128))
                            
                    except Exception as e:
                        continue
            
            if not polygons:
                QMessageBox.warning(self, "Warning", "No valid polygons found in the file.")
                return False
                
            self.polygons = polygons
            self.colors = colors
            # Initialize edge colors with default black for loaded polygons
            self.edge_colors = [QColor(0, 0, 0) for _ in polygons]
            self.calculate_bounds()
            self.zoom_to_fit()
            self.invalidate_cache()
            self.update()
            return True
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load file: {str(e)}")
            return False
    
    def load_background_image(self, image_path):
        """Load a background image"""
        try:
            from PyQt5.QtGui import QPixmap
            self.background_image = QPixmap(image_path)
            self.background_image_path = image_path
            
            if self.background_image.isNull():
                QMessageBox.critical(self, "Error", "Failed to load image file")
                return False
                
            return True
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load image: {str(e)}")
            return False
    
    def calculate_bounds(self):
        """Calculate the bounding box of all polygons"""
        if not self.polygons:
            self.original_bounds = QRectF(0, 0, 1000, 1000)
            return
        
        all_coords = []
        for polygon in self.polygons:
            coords = list(polygon.exterior.coords)
            all_coords.extend(coords)
        
        if all_coords:
            xs, ys = zip(*all_coords)
            min_x, max_x = min(xs), max(xs)
            min_y, max_y = min(ys), max(ys)
            
            # Add small margin
            width = max_x - min_x
            height = max_y - min_y
            margin = max(width, height) * 0.05
            
            self.original_bounds = QRectF(
                min_x - margin, 
                min_y - margin, 
                width + 2*margin, 
                height + 2*margin
            )
        else:
            self.original_bounds = QRectF(0, 0, 1000, 1000)
        
        # Invalidate cache
        self.cache_valid = False
    
    def invalidate_cache(self):
        """Mark the polygon cache as invalid"""
        self.cache_valid = False
    
    def get_viewport_bounds(self):
        """Get the current viewport bounds in world coordinates"""
        widget_width = self.width()
        widget_height = self.height()
        
        # Convert viewport corners to world coordinates
        top_left_x, top_left_y = self.screen_to_world(0, 0)
        bottom_right_x, bottom_right_y = self.screen_to_world(widget_width, widget_height)
        
        return QRectF(
            min(top_left_x, bottom_right_x),
            min(top_left_y, bottom_right_y),
            abs(bottom_right_x - top_left_x),
            abs(bottom_right_y - top_left_y)
        )
    
    def update_visible_polygons(self):
        """Update the list of visible polygon indices for viewport culling"""
        if not self.polygons:
            self.visible_indices = []
            return
        
        viewport = self.get_viewport_bounds()
        self.visible_indices = []
        
        for i, polygon in enumerate(self.polygons):
            # Get polygon bounds
            bounds = polygon.bounds  # (minx, miny, maxx, maxy)
            poly_rect = QRectF(bounds[0], bounds[1], bounds[2] - bounds[0], bounds[3] - bounds[1])
            
            # Check if polygon intersects viewport
            if viewport.intersects(poly_rect):
                self.visible_indices.append(i)
        
        # Update stats to reflect visible polygon count
        if hasattr(self, 'view_changed') and self.view_changed:
            self.update_stats_if_needed()
    
    def update_stats_if_needed(self):
        """Update stats display with current visible polygon count"""
        if hasattr(self, 'parent') and self.parent() and hasattr(self.parent(), 'control_panel'):
            # Get total polygon count and filename from control panel if available
            if hasattr(self.parent().control_panel, 'last_filename') and self.parent().control_panel.last_filename:
                total_count = len(self.polygons)
                self.parent().control_panel.update_stats(total_count, self.parent().control_panel.last_filename)
            else:
                self.parent().control_panel.update_stats(len(self.polygons))
    
    def zoom_to_fit(self):
        """Reset zoom to show all polygons"""
        if not self.original_bounds:
            return
        
        widget_width = self.width()
        widget_height = self.height()
        
        if widget_width == 0 or widget_height == 0:
            return
        
        # Calculate scale to fit
        scale_x = widget_width / self.original_bounds.width()
        scale_y = widget_height / self.original_bounds.height()
        self.scale_factor = min(scale_x, scale_y) * 0.9  # 90% to leave some margin
        
        # Center the view
        self.offset_x = (widget_width - self.original_bounds.width() * self.scale_factor) / 2 - self.original_bounds.x() * self.scale_factor
        self.offset_y = (widget_height - self.original_bounds.height() * self.scale_factor) / 2 - self.original_bounds.y() * self.scale_factor
        
        self.invalidate_cache()
        self.update()
        
        # Notify scale bars of view change
        if self.view_changed:
            self.view_changed()
    
    def world_to_screen(self, x, y):
        """Convert world coordinates to screen coordinates"""
        screen_x = x * self.scale_factor + self.offset_x
        screen_y = y * self.scale_factor + self.offset_y
        return screen_x, screen_y
    
    def screen_to_world(self, screen_x, screen_y):
        """Convert screen coordinates to world coordinates"""
        world_x = (screen_x - self.offset_x) / self.scale_factor
        world_y = (screen_y - self.offset_y) / self.scale_factor
        return world_x, world_y
    
    def find_polygon_at_point(self, screen_x, screen_y):
        """Find the polygon under the given screen coordinates"""
        world_x, world_y = self.screen_to_world(screen_x, screen_y)
        
        # Check polygons in reverse order (top to bottom)
        for i in reversed(self.visible_indices):
            if i >= len(self.polygons):
                continue
                
            polygon = self.polygons[i]
            
            # Skip small polygons
            if polygon.area < self.min_area:
                continue
                
            # Use shapely's contains method for accurate point-in-polygon test
            from shapely.geometry import Point
            point = Point(world_x, world_y)
            
            try:
                if polygon.contains(point) or polygon.boundary.distance(point) < (5.0 / self.scale_factor):
                    return i
            except:
                # Fallback to simple bounds check
                bounds = polygon.bounds
                if bounds[0] <= world_x <= bounds[2] and bounds[1] <= world_y <= bounds[3]:
                    return i
        
        return -1  # No polygon found
    
    def move_polygon(self, polygon_index, dx_world, dy_world):
        """Move a polygon by the given world coordinate offset"""
        if polygon_index < 0 or polygon_index >= len(self.polygons):
            return
            
        # Get the original polygon
        original_polygon = self.polygons[polygon_index]
        
        # Create a new polygon with translated coordinates
        from shapely.affinity import translate
        translated_polygon = translate(original_polygon, dx_world, dy_world)
        
        # Update the polygon
        self.polygons[polygon_index] = translated_polygon
        
        # Invalidate cache since geometry changed
        self.invalidate_cache()
    
    def erase_shapes_at_point(self, screen_x, screen_y):
        """Erase shapes at the given screen coordinates using eraser radius"""
        if not self.polygons:
            return
        
        world_x, world_y = self.screen_to_world(screen_x, screen_y)
        
        # Convert eraser radius from screen pixels to world coordinates
        world_radius = self.eraser_radius / self.scale_factor
        
        # Create a circle for intersection testing
        from shapely.geometry import Point
        eraser_point = Point(world_x, world_y)
        eraser_circle = eraser_point.buffer(world_radius)
        
        # Find polygons to remove
        indices_to_remove = []
        for i, polygon in enumerate(self.polygons):
            try:
                # Check if the polygon intersects with the eraser circle
                if polygon.intersects(eraser_circle):
                    indices_to_remove.append(i)
            except:
                # Fallback to simple distance check
                bounds = polygon.bounds
                poly_center_x = (bounds[0] + bounds[2]) / 2
                poly_center_y = (bounds[1] + bounds[3]) / 2
                distance = ((world_x - poly_center_x) ** 2 + (world_y - poly_center_y) ** 2) ** 0.5
                if distance <= world_radius:
                    indices_to_remove.append(i)
        
        # Remove polygons (in reverse order to maintain indices)
        if indices_to_remove:
            for i in reversed(indices_to_remove):
                del self.polygons[i]
                del self.colors[i]
            
            # Update visible indices and invalidate cache
            self.invalidate_cache()
            self.calculate_bounds()  # Recalculate bounds after deletion
    
    def paintEvent(self, event):
        """Paint the mosaic with optimized rendering"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        
        # Fill background with canvas background color (or default brightness)
        if hasattr(self, 'canvas_background_color'):
            painter.fillRect(self.rect(), self.canvas_background_color)
        else:
            bg_color = int(self.background_brightness * 255)
            painter.fillRect(self.rect(), QColor(bg_color, bg_color, bg_color))
        
        # Draw background image if loaded and visible
        if self.background_image and not self.background_image.isNull() and self.background_visible:
            if self.polygons:
                # If we have polygons, use world coordinate system with offset
                screen_x, screen_y = self.world_to_screen(self.background_offset_x, self.background_offset_y)
                scaled_width = self.background_image.width() * self.scale_factor
                scaled_height = self.background_image.height() * self.scale_factor
                painter.drawPixmap(int(screen_x), int(screen_y), 
                                 int(scaled_width), int(scaled_height), 
                                 self.background_image)
            else:
                # If no polygons, center the image in the widget with offset
                widget_center_x = self.width() // 2
                widget_center_y = self.height() // 2
                img_x = widget_center_x - self.background_image.width() // 2 + int(self.background_offset_x)
                img_y = widget_center_y - self.background_image.height() // 2 + int(self.background_offset_y)
                painter.drawPixmap(img_x, img_y, self.background_image)
        
        if not self.polygons:
            # Draw instructions
            painter.setPen(QPen(QColor(100, 100, 100), 1))
            painter.setFont(QFont('Arial', 14))
            painter.drawText(self.rect(), Qt.AlignCenter, 
                           "Load a CSV file to view mosaic\n\nControls:\n• Mouse wheel: Zoom\n• Left click + drag: Pan\n• Zoom to Fit button: Reset view")
            return
        
        # Update visible polygons for viewport culling
        self.update_visible_polygons()
        
        # Skip rendering if too many polygons are visible and we're at low zoom
        if len(self.visible_indices) > 5000 and self.scale_factor < 0.1:
            painter.setPen(QPen(QColor(100, 100, 100), 1))
            painter.setFont(QFont('Arial', 12))
            painter.drawText(self.rect(), Qt.AlignCenter, 
                           f"Zoom in to view details\n({len(self.polygons):,} polygons total)")
            return
        
        # Set up optimized rendering
        painter.save()
        
        # Draw grid box fills BEFORE polygons if Cut Tiles has been applied
        if hasattr(self, 'cut_tiles_applied') and self.cut_tiles_applied:
            self.draw_grid_box_fills(painter)
        
        # Draw only visible polygons
        polygons_drawn = 0
        max_polygons = 10000  # Limit for performance
        
        for i in self.visible_indices:
            if polygons_drawn >= max_polygons:
                break
                
            polygon = self.polygons[i]
            color = self.colors[i]
            edge_color = self.edge_colors[i] if i < len(self.edge_colors) else QColor(0, 0, 0)  # Default to black if no edge color
            
            # Skip polygons smaller than half_tile × half_tile
            if polygon.area < self.min_area:
                continue
            
            # Convert polygon coordinates to screen coordinates
            coords = list(polygon.exterior.coords)
            qt_polygon = QPolygonF()
            
            # Quick bounds check for very small polygons
            screen_coords = []
            for x, y in coords:
                screen_x, screen_y = self.world_to_screen(x, y)
                screen_coords.append((screen_x, screen_y))
                qt_polygon.append(QPointF(screen_x, screen_y))
            
            # Skip very small polygons when zoomed out
            if self.scale_factor < 1.0:
                # Calculate screen-space polygon size
                xs = [coord[0] for coord in screen_coords]
                ys = [coord[1] for coord in screen_coords]
                if xs and ys:
                    width = max(xs) - min(xs)
                    height = max(ys) - min(ys)
                    if width < 2 and height < 2:  # Skip tiny polygons
                        continue
            
            # Set brush for fill with optional transparency
            if self.transparent_shapes:
                # Create a fully transparent version of the color
                transparent_color = QColor(color.red(), color.green(), color.blue(), 0)  # Completely invisible
                painter.setBrush(QBrush(transparent_color))
            else:
                painter.setBrush(QBrush(color))
            
            # Highlight selected polygon
            if i == self.selected_polygon_index:
                # Draw with thin yellow highlight border
                highlight_pen = QPen(QColor(255, 255, 0), max(0.5, 1.0 * self.scale_factor))  # Thin yellow highlight
                painter.setPen(highlight_pen)
                painter.drawPolygon(qt_polygon)
            else:
                # Set pen based on edge visibility and use edge color
                if self.show_edges:
                    edge_pen = QPen(edge_color, max(0.5, self.edge_width * self.scale_factor))
                    painter.setPen(edge_pen)
                else:
                    painter.setPen(QPen(Qt.NoPen))
                # Draw normal polygon
                painter.drawPolygon(qt_polygon)
            
            polygons_drawn += 1
        
        painter.restore()
        
        # Draw performance info if many polygons were skipped
        if len(self.visible_indices) > max_polygons:
            painter.setPen(QPen(QColor(100, 100, 100), 1))
            painter.setFont(QFont('Arial', 10))
            painter.drawText(10, self.height() - 20, 
                           f"Showing {polygons_drawn:,} of {len(self.visible_indices):,} visible polygons")
        
        # Draw eraser cursor if in eraser mode
        if self.eraser_mode:
            cursor_pos = self.mapFromGlobal(self.cursor().pos())
            if self.rect().contains(cursor_pos):
                painter.setPen(QPen(QColor(255, 0, 0), 2))  # Red circle
                painter.setBrush(QBrush(Qt.NoBrush))  # No fill
                painter.drawEllipse(cursor_pos.x() - self.eraser_radius, 
                                  cursor_pos.y() - self.eraser_radius,
                                  self.eraser_radius * 2, 
                                  self.eraser_radius * 2)
        
        # Draw polygon cursor and current points if in polygon mode
        if self.polygon_mode:
            cursor_pos = self.mapFromGlobal(self.cursor().pos())
            if self.rect().contains(cursor_pos):
                # Draw square cursor
                painter.setPen(QPen(QColor(0, 255, 0), 2))  # Green square
                painter.setBrush(QBrush(Qt.NoBrush))  # No fill
                half_size = self.polygon_cursor_size // 2
                painter.drawRect(cursor_pos.x() - half_size, 
                               cursor_pos.y() - half_size,
                               self.polygon_cursor_size, 
                               self.polygon_cursor_size)
            
            # Draw current polygon points
            if self.polygon_points:
                painter.setPen(QPen(QColor(0, 255, 0), 3))  # Green points
                painter.setBrush(QBrush(QColor(0, 255, 0)))  # Green fill
                
                # Draw points
                for i, (world_x, world_y) in enumerate(self.polygon_points):
                    screen_x, screen_y = self.world_to_screen(world_x, world_y)
                    painter.drawEllipse(int(screen_x - 3), int(screen_y - 3), 6, 6)
                    
                    # Draw point number
                    painter.setPen(QPen(QColor(255, 255, 255), 1))
                    painter.setFont(QFont('Arial', 8, QFont.Bold))
                    painter.drawText(int(screen_x + 5), int(screen_y - 5), str(i + 1))
                    painter.setPen(QPen(QColor(0, 255, 0), 3))
                
                # Draw lines connecting points
                if len(self.polygon_points) > 1:
                    painter.setPen(QPen(QColor(0, 255, 0), 1))  # Thin green lines
                    for i in range(len(self.polygon_points) - 1):
                        x1, y1 = self.world_to_screen(*self.polygon_points[i])
                        x2, y2 = self.world_to_screen(*self.polygon_points[i + 1])
                        painter.drawLine(int(x1), int(y1), int(x2), int(y2))
                    
                    # If we have enough points, draw closing line
                    if len(self.polygon_points) >= 3:
                        x1, y1 = self.world_to_screen(*self.polygon_points[-1])
                        x2, y2 = self.world_to_screen(*self.polygon_points[0])
                        painter.drawLine(int(x1), int(y1), int(x2), int(y2))
                
                # Show progress
                painter.setPen(QPen(QColor(255, 255, 255), 1))
                painter.setFont(QFont('Arial', 12))
                if len(self.polygon_points) == 0:
                    progress_text = "Left-click to add points, right-click to finish"
                elif len(self.polygon_points) < 3:
                    progress_text = f"Polygon: {len(self.polygon_points)} points (need 3+ to finish)"
                else:
                    progress_text = f"Polygon: {len(self.polygon_points)} points (right-click to finish)"
                painter.drawText(10, 30, progress_text)
        
        # Draw grid if enabled
        if self.show_grid:
            self.draw_grid(painter)
        
        # Draw all box contours if any
        if hasattr(self, 'all_contours') and self.all_contours:
            # Use thin black lines
            line_width = max(0.5, 1.0 * self.scale_factor)
            painter.setPen(QPen(QColor(0, 0, 0), line_width))  # Thin black pen
            painter.setBrush(QBrush(Qt.NoBrush))  # No fill
            
            # Draw contours from all boxes
            for box_index, contours_list in self.all_contours.items():
                for contour_points in contours_list:
                    # Convert world coordinates to screen coordinates
                    screen_polygon = QPolygonF()
                    for point in contour_points:
                        world_x, world_y = point[0], point[1]
                        screen_x, screen_y = self.world_to_screen(world_x, world_y)
                        screen_polygon.append(QPointF(screen_x, screen_y))
                    
                    if screen_polygon.size() > 2:  # Only draw if we have enough points
                        painter.drawPolygon(screen_polygon)
        
        # Draw overlap highlights if in overlap check mode
        if hasattr(self, 'overlap_check_mode') and self.overlap_check_mode and hasattr(self, 'overlap_highlights'):
            painter.setPen(QPen(QColor(255, 0, 0), 3))  # Thick red pen with fixed width
            painter.setBrush(QBrush(Qt.NoBrush))  # No fill, just outline
            
            # Get set of all polygon indices that have overlaps
            overlapping_indices = set()
            for poly1_idx, poly2_idx in self.overlap_highlights:
                overlapping_indices.add(poly1_idx)
                overlapping_indices.add(poly2_idx)
            
            # Draw thick red outline for all overlapping polygons
            for poly_idx in overlapping_indices:
                if poly_idx < len(self.polygons):
                    polygon = self.polygons[poly_idx]
                    if polygon.is_valid:
                        # Convert polygon coordinates to screen coordinates
                        coords = list(polygon.exterior.coords)
                        screen_polygon = QPolygonF()
                        
                        for x, y in coords:
                            screen_x, screen_y = self.world_to_screen(x, y)
                            screen_polygon.append(QPointF(screen_x, screen_y))
                        
                        # Draw thick red outline
                        painter.drawPolygon(screen_polygon)
        
        # Draw control points for selected polygon
        if self.selected_polygon_index >= 0:
            self.draw_control_points(painter)
    
    def draw_grid(self, painter):
        """Draw the 6x6 grid overlay with draggable handle that scales with zoom"""
        
        # Calculate grid position and size in world coordinates
        # grid_size is now the size of each individual box/cell
        cell_size_world = self.grid_size
        total_grid_size_world = cell_size_world * 6  # 6 boxes = total grid size
        grid_x_world = self.grid_offset_x
        grid_y_world = self.grid_offset_y
        
        # Convert grid corners to screen coordinates
        grid_x_screen, grid_y_screen = self.world_to_screen(grid_x_world, grid_y_world)
        grid_end_x_screen, grid_end_y_screen = self.world_to_screen(
            grid_x_world + total_grid_size_world, grid_y_world + total_grid_size_world)
        
        # Calculate screen cell size
        cell_size_screen = (grid_end_x_screen - grid_x_screen) / 6
        
        # Draw grid lines
        painter.setPen(QPen(QColor(0, 0, 255), 2))  # Blue grid lines
        
        # Draw 6x6 grid (7 lines in each direction to create 6 boxes)
        for i in range(7):
            # Vertical lines
            x_screen = grid_x_screen + (i * cell_size_screen)
            painter.drawLine(int(x_screen), int(grid_y_screen), 
                           int(x_screen), int(grid_end_y_screen))
            
            # Horizontal lines
            y_screen = grid_y_screen + (i * cell_size_screen)
            painter.drawLine(int(grid_x_screen), int(y_screen), 
                           int(grid_end_x_screen), int(y_screen))
        
        
        # Draw column numbers (1-6) at the top of each column
        painter.setPen(QPen(QColor(0, 0, 255), 1))
        font = QFont()
        font.setPixelSize(max(12, int(cell_size_screen / 8)))  # Scale font with grid
        painter.setFont(font)
        
        for i in range(6):  # 6 columns
            column_center_x = grid_x_screen + (i + 0.5) * cell_size_screen
            number_y = grid_y_screen - 10  # Position above the grid
            painter.drawText(int(column_center_x - 5), int(number_y), str(i + 1))
        
        # Draw row letters (A-F) on the left side of each row
        for i in range(6):  # 6 rows
            row_center_y = grid_y_screen + (i + 0.5) * cell_size_screen
            letter_x = grid_x_screen - 20  # Position to the left of the grid
            painter.drawText(int(letter_x), int(row_center_y + 5), chr(ord('A') + i))
        
        # Draw draggable handle (small square in top-left corner)
        # Handle size scales with zoom but has min/max limits
        handle_size_world = max(10, min(50, 20 / self.scale_factor))
        handle_x_world = grid_x_world - handle_size_world / 2
        handle_y_world = grid_y_world - handle_size_world / 2
        
        handle_x_screen, handle_y_screen = self.world_to_screen(handle_x_world, handle_y_world)
        handle_end_x_screen, handle_end_y_screen = self.world_to_screen(
            handle_x_world + handle_size_world, handle_y_world + handle_size_world)
        
        handle_rect = QRect(int(handle_x_screen), int(handle_y_screen),
                           int(handle_end_x_screen - handle_x_screen),
                           int(handle_end_y_screen - handle_y_screen))
        
        # Fill handle with semi-transparent blue
        painter.fillRect(handle_rect, QColor(0, 0, 255, 128))
        
        # Draw handle border
        painter.setPen(QPen(QColor(0, 0, 255), 2))
        painter.drawRect(handle_rect)

    def draw_grid_box_fills(self, painter):
        """Draw filled grid boxes with assigned colors"""
        # Calculate grid position and size in world coordinates
        cell_size_world = self.grid_size
        total_grid_size_world = cell_size_world * 6  # 6x6 grid
        
        # Grid position (using grid offset)
        grid_x_world = self.grid_offset_x
        grid_y_world = self.grid_offset_y
        
        # Convert grid corners to screen coordinates
        grid_x_screen, grid_y_screen = self.world_to_screen(grid_x_world, grid_y_world)
        grid_end_x_screen, grid_end_y_screen = self.world_to_screen(
            grid_x_world + total_grid_size_world, grid_y_world + total_grid_size_world)
        
        # Calculate screen cell size
        cell_size_screen = (grid_end_x_screen - grid_x_screen) / 6
        
        # Define 36 rainbow colors with maximum distinction for better OpenCV detection
        grid_colors = [
            QColor(255, 0, 0),     # Pure Red
            QColor(255, 165, 0),   # Orange  
            QColor(255, 255, 0),   # Yellow
            QColor(128, 255, 0),   # Yellow-Green
            QColor(0, 255, 0),     # Pure Green
            QColor(0, 255, 128),   # Green-Cyan
            QColor(0, 255, 255),   # Cyan
            QColor(0, 128, 255),   # Light Blue
            QColor(0, 0, 255),     # Pure Blue
            QColor(128, 0, 255),   # Blue-Violet
            QColor(255, 0, 255),   # Magenta
            QColor(255, 0, 128),   # Pink
            QColor(128, 0, 0),     # Dark Red
            QColor(128, 82, 0),    # Dark Orange
            QColor(128, 128, 0),   # Dark Yellow/Olive
            QColor(64, 128, 0),    # Dark Yellow-Green
            QColor(0, 128, 0),     # Dark Green
            QColor(0, 128, 64),    # Dark Green-Cyan
            QColor(0, 128, 128),   # Dark Cyan/Teal
            QColor(0, 64, 128),    # Dark Light Blue
            QColor(0, 0, 128),     # Dark Blue/Navy
            QColor(64, 0, 128),    # Dark Violet
            QColor(128, 0, 128),   # Dark Magenta
            QColor(128, 0, 64),    # Dark Pink
            QColor(255, 128, 128), # Light Red
            QColor(255, 192, 128), # Light Orange
            QColor(255, 255, 128), # Light Yellow
            QColor(192, 255, 128), # Light Yellow-Green
            QColor(128, 255, 128), # Light Green
            QColor(128, 255, 192), # Light Green-Cyan
            QColor(128, 255, 255), # Light Cyan
            QColor(128, 192, 255), # Light Blue
            QColor(128, 128, 255), # Light Blue-Purple
            QColor(192, 128, 255), # Light Violet
            QColor(255, 128, 255), # Light Magenta
            QColor(255, 128, 192)  # Light Pink
        ]
        
        # Fill each grid box with its assigned color
        for row in range(6):
            for col in range(6):
                box_index = row * 6 + col
                box_color = grid_colors[box_index % len(grid_colors)]
                
                # Calculate box screen position
                box_x_screen = grid_x_screen + col * cell_size_screen
                box_y_screen = grid_y_screen + row * cell_size_screen
                
                # Create fully opaque fill color (no transparency)
                fill_color = QColor(box_color)
                fill_color.setAlpha(255)  # Full opacity
                
                painter.fillRect(
                    int(box_x_screen), int(box_y_screen),
                    int(cell_size_screen), int(cell_size_screen),
                    fill_color
                )
    
    def get_grid_handle_rect(self):
        """Get the rectangle for the grid handle in screen coordinates"""
        if not self.show_grid:
            return QRect()
            
        handle_size_world = max(10, min(50, 20 / self.scale_factor))
        handle_x_world = self.grid_offset_x - handle_size_world / 2
        handle_y_world = self.grid_offset_y - handle_size_world / 2
        
        handle_x_screen, handle_y_screen = self.world_to_screen(handle_x_world, handle_y_world)
        handle_end_x_screen, handle_end_y_screen = self.world_to_screen(
            handle_x_world + handle_size_world, handle_y_world + handle_size_world)
        
        return QRect(int(handle_x_screen), int(handle_y_screen),
                    int(handle_end_x_screen - handle_x_screen),
                    int(handle_end_y_screen - handle_y_screen))
    
    def draw_control_points(self, painter):
        """Draw control points for the selected polygon"""
        if (self.selected_polygon_index < 0 or 
            self.selected_polygon_index >= len(self.polygons)):
            return
            
        polygon = self.polygons[self.selected_polygon_index]
        
        # Draw control points as small circles
        painter.setPen(QPen(QColor(255, 0, 0), 2))  # Red outline
        painter.setBrush(QBrush(QColor(255, 255, 255, 200)))  # White fill with transparency
        
        # Get polygon coordinates (Shapely polygon exterior coords)
        coords = list(polygon.exterior.coords)[:-1]  # Remove duplicate last point
        
        for i, (x, y) in enumerate(coords):
            # Convert world coordinates to screen coordinates
            screen_x, screen_y = self.world_to_screen(x, y)
            
            # Calculate control point size in screen coordinates
            point_size = self.control_point_size
            
            # Highlight selected control point
            if i == self.selected_control_point:
                painter.setPen(QPen(QColor(255, 0, 0), 3))  # Thicker red outline
                painter.setBrush(QBrush(QColor(255, 0, 0, 150)))  # Red fill
            else:
                painter.setPen(QPen(QColor(255, 0, 0), 2))  # Normal red outline
                painter.setBrush(QBrush(QColor(255, 255, 255, 200)))  # White fill
            
            # Draw the control point circle
            painter.drawEllipse(int(screen_x - point_size/2), int(screen_y - point_size/2),
                              point_size, point_size)
    
    def find_control_point_at_screen_pos(self, screen_x, screen_y):
        """Find which control point is at the given screen position"""
        if (self.selected_polygon_index < 0 or 
            self.selected_polygon_index >= len(self.polygons)):
            return -1
            
        polygon = self.polygons[self.selected_polygon_index]
        
        # Get polygon coordinates (Shapely polygon exterior coords)
        coords = list(polygon.exterior.coords)[:-1]  # Remove duplicate last point
        
        for i, (x, y) in enumerate(coords):
            # Convert world coordinates to screen coordinates
            point_screen_x, point_screen_y = self.world_to_screen(x, y)
            
            # Check if click is within control point circle
            distance = ((screen_x - point_screen_x)**2 + (screen_y - point_screen_y)**2)**0.5
            if distance <= self.control_point_size:
                return i
                
        return -1
    
    def wheelEvent(self, event):
        """Handle mouse wheel for zooming with optimized performance"""
        if not self.polygons:
            return
        
        # Get mouse position
        mouse_pos = event.pos()
        
        # Convert to world coordinates before zoom
        world_x, world_y = self.screen_to_world(mouse_pos.x(), mouse_pos.y())
        
        # Apply zoom with larger steps for smoother performance
        zoom_factor = 1.2 if event.angleDelta().y() > 0 else 0.8
        old_scale = self.scale_factor
        self.scale_factor *= zoom_factor
        
        # Limit zoom range
        self.scale_factor = max(0.001, min(1000.0, self.scale_factor))
        
        # Adjust offset to zoom towards mouse position
        scale_change = self.scale_factor / old_scale
        self.offset_x = mouse_pos.x() - (mouse_pos.x() - self.offset_x) * scale_change
        self.offset_y = mouse_pos.y() - (mouse_pos.y() - self.offset_y) * scale_change
        
        self.invalidate_cache()
        
        # Use a timer to reduce update frequency during rapid scrolling
        if not hasattr(self, '_zoom_timer'):
            from PyQt5.QtCore import QTimer
            self._zoom_timer = QTimer()
            self._zoom_timer.setSingleShot(True)
            self._zoom_timer.timeout.connect(self.update)
        
        self._zoom_timer.stop()
        self._zoom_timer.start(16)  # ~60 FPS max update rate
        
        # Notify scale bars of view change
        if self.view_changed:
            self.view_changed()
    
    def mousePressEvent(self, event):
        """Handle mouse press for grid dragging, shape selection/dragging, panning, erasing, or polygon drawing"""
        if event.button() == Qt.LeftButton:
            # Check if clicking on grid handle first
            if self.show_grid and self.get_grid_handle_rect().contains(event.pos()):
                self.grid_dragging = True
                self.grid_drag_start = event.pos()
                self.grid_drag_world_start = self.screen_to_world(event.x(), event.y())
                self.setCursor(Qt.ClosedHandCursor)
                return
                
            if self.paint_mode:
                # Paint mode - find polygon and paint it, then start drag painting
                polygon_index = self.find_polygon_at_point(event.x(), event.y())
                if polygon_index >= 0:
                    self.paint_polygon(polygon_index)
                    self.last_painted_polygon = polygon_index
                
                # Start paint dragging mode
                self.is_painting = True
                return
                
            if self.eraser_mode:
                # Start erasing shapes
                self.is_erasing = True
                self.erase_shapes_at_point(event.x(), event.y())
                self.update()  # Refresh to show changes
            elif self.polygon_mode:
                # In polygon mode, left click adds point to polygon
                self.add_polygon_point(event.x(), event.y())
                self.update()  # Refresh to show new point
            else:
                # Normal mode - first check if clicking on a control point of selected polygon
                control_point_index = -1
                if self.selected_polygon_index >= 0:
                    control_point_index = self.find_control_point_at_screen_pos(event.x(), event.y())
                
                if control_point_index >= 0:
                    # Start dragging the selected control point
                    self.selected_control_point = control_point_index
                    self.is_dragging_control_point = True
                    self.last_drag_point = event.pos()
                    self.drag_start_world_pos = self.screen_to_world(event.x(), event.y())
                    self.setCursor(Qt.ClosedHandCursor)
                    self.update()  # Refresh to show control point selection
                else:
                    # Not clicking on control point, try to find a polygon under the cursor
                    polygon_index = self.find_polygon_at_point(event.x(), event.y())
                    
                    if polygon_index >= 0:
                        # Start dragging the selected shape
                        self.selected_polygon_index = polygon_index
                        self.selected_control_point = -1  # Clear control point selection
                        self.is_dragging_shape = True
                        self.last_drag_point = event.pos()
                        self.drag_start_world_pos = self.screen_to_world(event.x(), event.y())
                        self.setCursor(Qt.ClosedHandCursor)
                        self.update()  # Refresh to show selection highlight
                    else:
                        # No shape found, start panning the view
                        self.selected_polygon_index = -1  # Clear selection
                        self.selected_control_point = -1  # Clear control point selection
                        self.last_pan_point = event.pos()
                        self.is_panning = True
                        self.setCursor(Qt.ClosedHandCursor)
                        self.update()  # Refresh to clear any selection highlight
                    self.update()  # Refresh to clear any selection highlight
        
        elif event.button() == Qt.RightButton:
            if self.polygon_mode:
                # Right click finishes the polygon
                self.finish_polygon()
    
    def mouseMoveEvent(self, event):
        """Handle mouse move for grid dragging, shape dragging, view panning, erasing, painting, or cursor updates"""
        if self.is_painting:
            # Paint mode dragging - paint any polygon under the cursor
            polygon_index = self.find_polygon_at_point(event.x(), event.y())
            if polygon_index >= 0 and polygon_index != self.last_painted_polygon:
                self.paint_polygon(polygon_index)
                self.last_painted_polygon = polygon_index
            return
            
        elif self.grid_dragging and self.grid_drag_world_start:
            # Drag the grid in world coordinates
            current_world_pos = self.screen_to_world(event.x(), event.y())
            dx_world = current_world_pos[0] - self.grid_drag_world_start[0]
            dy_world = current_world_pos[1] - self.grid_drag_world_start[1]
            
            self.grid_offset_x += dx_world
            self.grid_offset_y += dy_world
            self.grid_drag_world_start = current_world_pos
            self.update()
            
        elif self.is_dragging_control_point and self.selected_control_point >= 0:
            # Drag the selected control point
            current_world_pos = self.screen_to_world(event.x(), event.y())
            
            # Update the control point position by recreating the Shapely polygon
            if (self.selected_polygon_index >= 0 and 
                self.selected_polygon_index < len(self.polygons)):
                
                polygon = self.polygons[self.selected_polygon_index]
                coords = list(polygon.exterior.coords)[:-1]  # Remove duplicate last point
                
                if self.selected_control_point < len(coords):
                    # Update the selected control point
                    coords[self.selected_control_point] = current_world_pos
                    
                    # Close the polygon by adding the first point at the end
                    coords.append(coords[0])
                    
                    # Create new Shapely polygon
                    from shapely.geometry import Polygon
                    self.polygons[self.selected_polygon_index] = Polygon(coords)
                    
                    self.invalidate_cache()  # Clear cache since polygon changed
                    self.update()
            
        elif self.eraser_mode:
            # Update eraser cursor position
            from PyQt5.QtGui import QPainterPath
            from PyQt5.QtCore import QRectF
            
            # Remove previous cursor if it exists
            if self.eraser_cursor is not None:
                self.eraser_cursor = None
            
            # If currently erasing, continue erasing
            if self.is_erasing:
                self.erase_shapes_at_point(event.x(), event.y())
                self.update()  # Refresh to show changes
            else:
                # Just update the cursor - the paintEvent will draw the circle
                self.update()
                
        elif self.is_dragging_shape and self.last_drag_point:
            # Drag the selected shape
            current_world_pos = self.screen_to_world(event.x(), event.y())
            dx_world = current_world_pos[0] - self.drag_start_world_pos[0]
            dy_world = current_world_pos[1] - self.drag_start_world_pos[1]
            
            # Move the polygon
            self.move_polygon(self.selected_polygon_index, dx_world, dy_world)
            
            # Update drag start position for next move
            self.drag_start_world_pos = current_world_pos
            
            # Update display
            self.update()
            
        elif self.is_panning and self.last_pan_point:
            # Pan the view
            delta = event.pos() - self.last_pan_point
            self.offset_x += delta.x()
            self.offset_y += delta.y()
            self.last_pan_point = event.pos()
            
            self.invalidate_cache()
            
            # Reduce update frequency during panning for better performance
            if not hasattr(self, '_pan_timer'):
                from PyQt5.QtCore import QTimer
                self._pan_timer = QTimer()
                self._pan_timer.setSingleShot(True)
                self._pan_timer.timeout.connect(self.update)
            
            self._pan_timer.stop()
            self._pan_timer.start(16)  # ~60 FPS max update rate
            
            # Notify scale bars of view change
            if self.view_changed:
                self.view_changed()
        else:
            # Just hovering - update for cursor if needed
            if self.eraser_mode or self.polygon_mode:
                self.update()
    
    def mouseReleaseEvent(self, event):
        """Handle mouse release"""
        if event.button() == Qt.LeftButton:
            if self.is_painting:
                # Finish painting
                self.is_painting = False
                self.last_painted_polygon = -1  # Reset for next paint session
            elif self.grid_dragging:
                # Finish dragging grid
                self.grid_dragging = False
                self.grid_drag_start = None
                self.grid_drag_world_start = None
            elif self.is_dragging_control_point:
                # Finish dragging control point
                self.is_dragging_control_point = False
                self.last_drag_point = None
                self.drag_start_world_pos = None
            elif self.is_erasing:
                # Finish erasing
                self.is_erasing = False
            elif self.is_dragging_shape:
                # Finish dragging shape
                self.is_dragging_shape = False
                self.last_drag_point = None
                self.drag_start_world_pos = None
            elif self.is_panning:
                # Finish panning view
                self.is_panning = False
                self.last_pan_point = None
            
            # Set appropriate cursor
            if self.eraser_mode:
                self.setCursor(Qt.BlankCursor)  # Hide cursor in eraser mode, we draw our own
            elif self.polygon_mode:
                self.setCursor(Qt.BlankCursor)  # Hide cursor in polygon mode, we draw our own
            elif self.paint_mode:
                self.setCursor(Qt.CrossCursor)  # Crosshair cursor in paint mode
            else:
                self.setCursor(Qt.ArrowCursor)
    
    def clear_selection(self):
        """Clear the current polygon selection"""
        if self.selected_polygon_index >= 0:
            self.selected_polygon_index = -1
            self.update()
    
    def toggle_eraser_mode(self):
        """Toggle eraser mode on/off"""
        self.eraser_mode = not self.eraser_mode
        
        if self.eraser_mode:
            # Entering eraser mode - disable other modes
            self.polygon_mode = False
            self.paint_mode = False
            self.polygon_points = []
            self.setCursor(Qt.BlankCursor)  # Hide cursor, we'll draw our own
            self.clear_selection()  # Clear any current selection
            # Cancel any ongoing drag operations
            self.is_dragging_shape = False
            self.is_panning = False
            self.last_drag_point = None
            self.last_pan_point = None
            self.drag_start_world_pos = None
        else:
            # Exiting eraser mode
            self.setCursor(Qt.ArrowCursor)  # Restore normal cursor
            self.is_erasing = False
        
        self.update()  # Refresh display
    
    def toggle_paint_mode(self):
        """Toggle paint mode on/off"""
        self.paint_mode = not self.paint_mode
        
        if self.paint_mode:
            # Entering paint mode - disable other modes
            self.eraser_mode = False
            self.polygon_mode = False
            self.polygon_points = []
            self.setCursor(Qt.CrossCursor)  # Set crosshair cursor
            self.clear_selection()  # Clear any current selection
            # Cancel any ongoing drag operations
            self.is_dragging_shape = False
            self.is_panning = False
            self.is_dragging_control_point = False
            self.grid_dragging = False
            self.last_drag_point = None
            self.last_pan_point = None
            self.drag_start_world_pos = None
        else:
            # Exiting paint mode
            self.setCursor(Qt.ArrowCursor)  # Restore normal cursor
        
        self.update()  # Refresh display
    
    def paint_polygon(self, polygon_index):
        """Paint a polygon with the selected color from the palette"""
        if polygon_index >= 0 and polygon_index < len(self.colors):
            # Use the selected color from the palette if available, otherwise use black
            paint_color = getattr(self, 'selected_palette_color', QColor(0, 0, 0))
            self.colors[polygon_index] = paint_color
            self.invalidate_cache()  # Clear cache since color changed
            self.update()  # Refresh display
    
    def toggle_polygon_mode(self):
        """Toggle polygon drawing mode on/off"""
        self.polygon_mode = not self.polygon_mode
        
        if self.polygon_mode:
            # Entering polygon mode - disable other modes
            self.eraser_mode = False
            self.paint_mode = False
            self.is_erasing = False
            self.polygon_points = []  # Reset points
            self.setCursor(Qt.BlankCursor)  # Hide cursor, we'll draw our own
            self.clear_selection()  # Clear any current selection
            # Cancel any ongoing drag operations
            self.is_dragging_shape = False
            self.is_panning = False
            self.last_drag_point = None
            self.last_pan_point = None
            self.drag_start_world_pos = None #fff
        else:
            # Exiting polygon mode
            self.setCursor(Qt.ArrowCursor)  # Restore normal cursor
            self.polygon_points = []  # Clear any points
        
        self.update()  # Refresh display
    
    def add_polygon_point(self, screen_x, screen_y):
        """Add a point to the current polygon being drawn"""
        if not self.polygon_mode:
            return
            
        # Convert screen coordinates to world coordinates
        world_x, world_y = self.screen_to_world(screen_x, screen_y)
        self.polygon_points.append((world_x, world_y))
    
    def finish_polygon(self):
        """Finish the current polygon if we have enough points"""
        if len(self.polygon_points) >= 3:
            self.create_polygon_from_points()
        elif len(self.polygon_points) > 0:
            # Have some points but not enough
            # Keep the points, don't clear them - user might want to add more
            pass
        # If no points, do nothing silently
    
    def get_average_color_from_background(self, polygon):
        """Get color from background image at polygon center point"""
        from PyQt5.QtGui import QColor
        
        # Default to transparent gray if no background image
        if not self.background_image or self.background_image.isNull():
            return QColor(128, 128, 128, 0)  # Transparent gray
        
        try:
            # Convert QPixmap to QImage for pixel access
            background_image = self.background_image.toImage()
            
            # Get polygon centroid (center point)
            centroid = polygon.centroid
            center_world_x = centroid.x
            center_world_y = centroid.y
            
            # Convert world coordinates to screen coordinates, then to image coordinates
            # This matches exactly how the background image is drawn
            img_screen_x, img_screen_y = self.world_to_screen(self.background_offset_x, self.background_offset_y)
            center_screen_x, center_screen_y = self.world_to_screen(center_world_x, center_world_y)
            
            # Calculate relative position within the scaled image
            relative_screen_x = center_screen_x - img_screen_x
            relative_screen_y = center_screen_y - img_screen_y
            
            # Convert back to original image coordinates
            img_x = int(relative_screen_x / self.scale_factor)
            img_y = int(relative_screen_y / self.scale_factor)
            
            # Ensure coordinates are within image bounds
            img_width = background_image.width()
            img_height = background_image.height()
            
            if img_x < 0 or img_x >= img_width or img_y < 0 or img_y >= img_height:
                return QColor(255, 0, 255)  # Magenta to indicate out of bounds
            
            # Sample pixel color at center point
            pixel_color = background_image.pixel(img_x, img_y)
            
            # Extract RGB values from QRgb
            from PyQt5.QtGui import qRed, qGreen, qBlue
            r = qRed(pixel_color)
            g = qGreen(pixel_color)
            b = qBlue(pixel_color)
            
            return QColor(r, g, b)  # Opaque color
            
        except Exception as e:
            return QColor(255, 0, 0)  # Red to indicate error
    
    def create_polygon_from_points(self):
        """Create a polygon from the collected points"""
        if len(self.polygon_points) < 3:
            return  # Need at least 3 points for a polygon
        
        try:
            # Create polygon from points
            from shapely.geometry import Polygon
            polygon = Polygon(self.polygon_points)
            
            # Make sure the polygon is valid
            if polygon.is_valid and polygon.area > 0:
                # Always get fill color from background image or use default
                fill_color = self.get_average_color_from_background(polygon)
                
                # Use selected palette color for edge/frame if available
                if hasattr(self, 'selected_palette_color') and self.selected_palette_color:
                    edge_color = self.selected_palette_color
                else:
                    # Default edge color (black)
                    edge_color = QColor(0, 0, 0)
                
                self.polygons.append(polygon)
                self.colors.append(fill_color)
                self.edge_colors.append(edge_color)
                
                # Update bounds and cache
                self.calculate_bounds()
                self.invalidate_cache()
                
                # Trigger statistics update if there's a callback
                if hasattr(self, 'statistics_callback') and self.statistics_callback:
                    self.statistics_callback()
            else:
                pass
                
        except Exception as e:
            pass
        
        # Reset points for next polygon
        self.polygon_points = []
        self.update()
    
    def delete_selected_polygon(self):
        """Delete the currently selected polygon"""
        if self.selected_polygon_index >= 0 and self.selected_polygon_index < len(self.polygons):
            # Remove polygon and its color
            del self.polygons[self.selected_polygon_index]
            del self.colors[self.selected_polygon_index]
            # Also remove edge color
            if self.selected_polygon_index < len(self.edge_colors):
                del self.edge_colors[self.selected_polygon_index]
            
            # Clear selection
            self.selected_polygon_index = -1
            
            # Update bounds and cache
            self.calculate_bounds()
            self.invalidate_cache()
            self.update()
            
            # Trigger statistics update if there's a callback
            if hasattr(self, 'statistics_callback') and self.statistics_callback:
                self.statistics_callback()
    
    def keyPressEvent(self, event):
        """Handle key press events"""
        if event.key() == Qt.Key_Escape:
            # Clear selection on Escape key
            self.clear_selection()
            # Also clear polygon points if in polygon mode
            if self.polygon_mode and self.polygon_points:
                self.polygon_points = []
                self.update()
            # Exit all modes and return to normal cursor
            if hasattr(self, 'main_editor') and self.main_editor:
                self.main_editor.exit_all_modes()
        elif event.key() == Qt.Key_Delete and self.selected_polygon_index >= 0:
            # Delete selected polygon on Delete key
            self.delete_selected_polygon()
        else:
            super().keyPressEvent(event)
    
    def get_visible_polygons_with_colors(self):
        """Get all polygons and their colors that meet minimum area requirement (regardless of viewport)"""
        if not self.polygons:
            return [], []
        
        visible_polygons = []
        visible_colors = []
        
        # Check all polygons, not just viewport-visible ones
        for i in range(len(self.polygons)):
            polygon = self.polygons[i]
            
            # Only include polygons that meet minimum area requirement
            if polygon.area >= self.min_area:
                visible_polygons.append(polygon)
                visible_colors.append(self.colors[i])
        
        return visible_polygons, visible_colors
    
    def resizeEvent(self, event):
        """Handle widget resize"""
        super().resizeEvent(event)
        if self.polygons and self.original_bounds:
            # Maintain center point when resizing
            self.update()


class CanvasWithScaleBars(QWidget):
    """Container widget that includes the main canvas and scale bars"""
    
    def __init__(self):
        super().__init__()
        self.setup_ui()
    
    def setup_ui(self):
        """Set up the layout with canvas and scale bars"""
        layout = QGridLayout(self)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Create main canvas only - scale bars removed as requested
        self.canvas = MosaicCanvas()
        
        # Add only the canvas, no scale bars
        layout.addWidget(self.canvas, 0, 0)
        
        # Set stretch factors so canvas takes all space
        layout.setRowStretch(0, 1)
        layout.setColumnStretch(0, 1)
        
        # Connect canvas changes to scale bar updates
        self.canvas.view_changed = self.update_scale_bars
        
        # No scale bars to initialize - removed as requested
    
    def update_scale_bars(self):
        """Update scale bars when the view changes"""
        # Scale bars removed - method kept for compatibility
        pass


class TopScaleBar(QWidget):
    """Horizontal scale bar at the top"""
    
    def __init__(self):
        super().__init__()
        self.setFixedHeight(30)
        self.min_val = 0
        self.max_val = 100
        self.scale_factor = 1.0
    
    def update_scale(self, min_val, max_val, scale_factor):
        """Update the scale range"""
        self.min_val = min_val
        self.max_val = max_val
        self.scale_factor = scale_factor
        self.update()
    
    def paintEvent(self, event):
        """Paint the horizontal scale bar"""
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(240, 240, 240))
        
        # Draw scale markings
        painter.setPen(QPen(QColor(100, 100, 100), 1))
        painter.setFont(QFont('Arial', 8))
        
        width = self.width()
        range_val = self.max_val - self.min_val
        
        if range_val > 0:
            # Calculate nice tick spacing
            tick_spacing = self.calculate_tick_spacing(range_val, width)
            
            # Draw ticks and labels
            start_tick = int(self.min_val / tick_spacing) * tick_spacing
            tick_val = start_tick
            
            while tick_val <= self.max_val:
                x_pos = int((tick_val - self.min_val) / range_val * width)
                if 0 <= x_pos <= width:
                    # Draw tick mark
                    painter.drawLine(x_pos, 20, x_pos, 30)
                    
                    # Draw label
                    label = f"{tick_val:.0f}" if tick_val >= 1 else f"{tick_val:.1f}"
                    painter.drawText(x_pos - 15, 15, 30, 10, Qt.AlignCenter, label)
                
                tick_val += tick_spacing
    
    def calculate_tick_spacing(self, range_val, width_pixels):
        """Calculate appropriate tick spacing"""
        target_ticks = width_pixels / 80  # One tick every ~80 pixels
        raw_spacing = range_val / target_ticks
        
        # Round to nice numbers
        magnitude = 10 ** int(np.log10(raw_spacing))
        normalized = raw_spacing / magnitude
        
        if normalized <= 1:
            nice_spacing = 1
        elif normalized <= 2:
            nice_spacing = 2
        elif normalized <= 5:
            nice_spacing = 5
        else:
            nice_spacing = 10
        
        return nice_spacing * magnitude


class LeftScaleBar(QWidget):
    """Vertical scale bar on the left"""
    
    def __init__(self):
        super().__init__()
        self.setFixedWidth(50)
        self.min_val = 0
        self.max_val = 100
        self.scale_factor = 1.0
    
    def update_scale(self, min_val, max_val, scale_factor):
        """Update the scale range"""
        self.min_val = min_val
        self.max_val = max_val
        self.scale_factor = scale_factor
        self.update()
    
    def paintEvent(self, event):
        """Paint the vertical scale bar"""
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(240, 240, 240))
        
        # Draw scale markings
        painter.setPen(QPen(QColor(100, 100, 100), 1))
        painter.setFont(QFont('Arial', 8))
        
        height = self.height()
        range_val = self.max_val - self.min_val
        
        if range_val > 0:
            # Calculate nice tick spacing
            tick_spacing = self.calculate_tick_spacing(range_val, height)
            
            # Draw ticks and labels
            start_tick = int(self.min_val / tick_spacing) * tick_spacing
            tick_val = start_tick
            
            while tick_val <= self.max_val:
                y_pos = int((tick_val - self.min_val) / range_val * height)
                if 0 <= y_pos <= height:
                    # Draw tick mark
                    painter.drawLine(40, height - y_pos, 50, height - y_pos)
                    
                    # Draw label
                    label = f"{tick_val:.0f}" if tick_val >= 1 else f"{tick_val:.1f}"
                    painter.save()
                    painter.translate(25, height - y_pos)
                    painter.rotate(-90)
                    painter.drawText(-15, -5, 30, 10, Qt.AlignCenter, label)
                    painter.restore()
                
                tick_val += tick_spacing
    
    def calculate_tick_spacing(self, range_val, height_pixels):
        """Calculate appropriate tick spacing"""
        target_ticks = height_pixels / 60  # One tick every ~60 pixels
        raw_spacing = range_val / target_ticks
        
        # Round to nice numbers
        magnitude = 10 ** int(np.log10(raw_spacing))
        normalized = raw_spacing / magnitude
        
        if normalized <= 1:
            nice_spacing = 1
        elif normalized <= 2:
            nice_spacing = 2
        elif normalized <= 5:
            nice_spacing = 5
        else:
            nice_spacing = 10
        
        return nice_spacing * magnitude


class ControlPanel(QWidget):
    """Control panel for mosaic settings"""
    
    # Signals
    edges_toggled = pyqtSignal(bool)
    edge_width_changed = pyqtSignal(float)
    transparent_toggled = pyqtSignal(bool)
    background_image_loaded = pyqtSignal(str)
    background_offset_changed = pyqtSignal(float, float)
    background_visible_toggled = pyqtSignal(bool)
    min_area_changed = pyqtSignal(float)
    save_visible_requested = pyqtSignal()
    eraser_toggled = pyqtSignal(bool)
    polygon_toggled = pyqtSignal(bool)
    grid_toggled = pyqtSignal(bool)
    grid_size_changed = pyqtSignal(int)
    paint_toggled = pyqtSignal(bool)
    
    def __init__(self, canvas=None):
        super().__init__()
        self.canvas = canvas  # Store canvas reference directly
        self.last_filename = None  # Track last loaded filename for stats updates
        self.setup_ui()
    
    def setup_ui(self):
        """Set up the control panel UI"""
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # File Operations
        layout.addWidget(QLabel('File Operations:', font=QFont('Arial', 10, QFont.Bold)))
        
        self.load_btn = QPushButton("Load CSV File")
        layout.addWidget(self.load_btn)
        
        self.save_btn = QPushButton("Save Visible Array")
        self.save_btn.setEnabled(False)  # Disabled until file is loaded
        layout.addWidget(self.save_btn)
        
        self.load_image_btn = QPushButton("Load Background Image")
        layout.addWidget(self.load_image_btn)
        
        # Minimum area setting
        layout.addWidget(QLabel('Minimum Tile Area:'))
        self.min_area_input = QLineEdit()
        self.min_area_input.setText('30')
        self.min_area_input.setPlaceholderText('Enter minimum area (e.g., 30)')
        self.min_area_input.textChanged.connect(self.on_min_area_changed)
        layout.addWidget(self.min_area_input)
        
        layout.addWidget(self.create_separator())
        layout.addWidget(QLabel('Background Offset:'))
        
        offset_layout = QHBoxLayout()
        offset_layout.addWidget(QLabel('X:'))
        self.bg_offset_x_input = QLineEdit()
        self.bg_offset_x_input.setText('0')  # Will be updated in sync_ui_with_canvas
        self.bg_offset_x_input.setPlaceholderText('X offset')
        self.bg_offset_x_input.textChanged.connect(self.on_background_offset_changed)
        offset_layout.addWidget(self.bg_offset_x_input)
        
        offset_layout.addWidget(QLabel('Y:'))
        self.bg_offset_y_input = QLineEdit()
        self.bg_offset_y_input.setText('0')  # Will be updated in sync_ui_with_canvas
        self.bg_offset_y_input.setPlaceholderText('Y offset')
        self.bg_offset_y_input.textChanged.connect(self.on_background_offset_changed)
        offset_layout.addWidget(self.bg_offset_y_input)
        
        offset_widget = QWidget()
        offset_widget.setLayout(offset_layout)
        layout.addWidget(offset_widget)
        
        # Background image visibility checkbox
        self.background_visible_checkbox = QCheckBox('Show Background Image')
        self.background_visible_checkbox.setChecked(True)
        self.background_visible_checkbox.toggled.connect(self.background_visible_toggled.emit)
        layout.addWidget(self.background_visible_checkbox)
        
        layout.addWidget(self.create_separator())
        
        # Display Settings
        layout.addWidget(QLabel('Display Settings:', font=QFont('Arial', 10, QFont.Bold)))
        
        # Show edges checkbox
        self.edge_checkbox = QCheckBox('Show Edges')
        self.edge_checkbox.setChecked(True)
        self.edge_checkbox.toggled.connect(self.edges_toggled.emit)
        layout.addWidget(self.edge_checkbox)
        
        # Edge width text input
        layout.addWidget(QLabel('Edge Width:'))
        self.edge_width_input = QLineEdit()
        self.edge_width_input.setText('0.1')  # Changed default from '1.0' to '0.1'
        self.edge_width_input.setPlaceholderText('Enter edge width (e.g., 0.1)')
        self.edge_width_input.textChanged.connect(self.on_edge_width_text_changed)
        layout.addWidget(self.edge_width_input)
        
        # Transparent checkbox
        self.transparent_checkbox = QCheckBox('Transparent Shapes')
        self.transparent_checkbox.setChecked(False)
        self.transparent_checkbox.toggled.connect(self.transparent_toggled.emit)
        layout.addWidget(self.transparent_checkbox)
        
        # Eraser mode checkbox
        self.eraser_checkbox = QCheckBox('Eraser Mode')
        self.eraser_checkbox.setChecked(False)
        self.eraser_checkbox.toggled.connect(self.eraser_toggled.emit)
        layout.addWidget(self.eraser_checkbox)
        
        # Polygon drawing mode checkbox
        self.polygon_checkbox = QCheckBox('Polygon Mode')
        self.polygon_checkbox.setChecked(False)
        self.polygon_checkbox.toggled.connect(self.polygon_toggled.emit)
        layout.addWidget(self.polygon_checkbox)
        
        # Paint mode checkbox
        self.paint_checkbox = QCheckBox('Paint Mode')
        self.paint_checkbox.setChecked(False)
        self.paint_checkbox.toggled.connect(self.on_paint_toggled)
        layout.addWidget(self.paint_checkbox)
        
        layout.addWidget(self.create_separator())
        
        # Grid Settings
        layout.addWidget(QLabel('Grid Settings:', font=QFont('Arial', 10, QFont.Bold)))
        
        # Grid toggle button
        self.grid_checkbox = QCheckBox('Show Grid')
        self.grid_checkbox.setChecked(False)
        self.grid_checkbox.toggled.connect(self.on_grid_toggled)
        layout.addWidget(self.grid_checkbox)
        
        # Grid size input
        layout.addWidget(QLabel('Box Size:'))
        self.grid_size_input = QLineEdit()
        self.grid_size_input.setText('300')
        self.grid_size_input.setPlaceholderText('Enter box size (e.g.,300)')
        self.grid_size_input.textChanged.connect(self.on_grid_size_changed)
    
        layout.addWidget(self.grid_size_input)
        
        layout.addWidget(self.create_separator())
        
        layout.addWidget(self.create_separator())
        
        # Statistics
        layout.addWidget(QLabel('Statistics:', font=QFont('Arial', 10, QFont.Bold)))
        
        self.stats_label = QLabel('No file loaded')
        self.stats_label.setWordWrap(True)
        layout.addWidget(self.stats_label)
        
        # Initialize UI with canvas default values
        if self.canvas:
            self.sync_ui_with_canvas()
        
        # Add stretch to push everything up
        layout.addStretch()
    
    def create_separator(self):
        """Create a visual separator line"""
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        return line
    
    def sync_ui_with_canvas(self):
        """Synchronize UI input fields with canvas default values"""
        if self.canvas:
            # Temporarily disconnect signals to avoid triggering updates
            self.bg_offset_x_input.textChanged.disconnect()
            self.bg_offset_y_input.textChanged.disconnect()
            
            # Update UI values to match canvas
            self.bg_offset_x_input.setText(str(self.canvas.background_offset_x))
            self.bg_offset_y_input.setText(str(self.canvas.background_offset_y))
            
            # Reconnect signals
            self.bg_offset_x_input.textChanged.connect(self.on_background_offset_changed)
            self.bg_offset_y_input.textChanged.connect(self.on_background_offset_changed)
            
            # Trigger a canvas update to ensure proper display
            self.canvas.update()
    
    def on_edge_width_text_changed(self, text):
        """Handle edge width text input change"""
        try:
            width = float(text) if text else 1.0
            width = max(0.1, min(10.0, width))  # Limit range
            self.edge_width_changed.emit(width)
        except ValueError:
            # Invalid input, ignore
            pass
    
    def update_stats(self, num_polygons, filename=None):
        """Update statistics display"""
        if filename:
            self.last_filename = filename  # Store filename for later use
            # Count how many polygons are actually visible on the canvas
            has_canvas = self.canvas is not None
            
            if has_canvas:
                has_polygons = self.canvas.polygons
            
            if self.canvas and self.canvas.polygons:
                canvas = self.canvas
                
                # Count visible polygons that also meet minimum area requirement
                visible_count = 0
                for i in canvas.visible_indices:
                    if i < len(canvas.polygons):
                        poly_area = canvas.polygons[i].area
                        meets_min_area = poly_area >= canvas.min_area
                        if meets_min_area:
                            visible_count += 1
                
                # Count total polygons that meet minimum area requirement
                total_qualifying = 0
                for i, polygon in enumerate(canvas.polygons):
                    meets_min_area = polygon.area >= canvas.min_area
                    if meets_min_area:
                        total_qualifying += 1
                
                filtered_out = total_qualifying - visible_count
                stats_text = f"File: {filename}\nTotal tiles: {total_qualifying:,}\nVisible tiles: {visible_count:,}\nFiltered out: {filtered_out:,}\nMin area: {canvas.min_area:.0f}"
            else:
                stats_text = f"File: {filename}\nTiles: {num_polygons:,}"
            # Enable save button when file is loaded
            self.save_btn.setEnabled(True)
        else:
            stats_text = f"Tiles: {num_polygons:,}"
        
        self.stats_label.setText(stats_text)
    
    def load_background_image(self):
        """Load a background image"""
        from PyQt5.QtWidgets import QFileDialog
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Load Background Image",
            "",
            "Image Files (*.png *.jpg *.jpeg *.bmp *.tiff);;All Files (*)"
        )
        
        if filename:
            self.background_image_loaded.emit(filename)
    
    def on_background_offset_changed(self):
        """Handle background image offset changes"""
        try:
            x_offset = float(self.bg_offset_x_input.text()) if self.bg_offset_x_input.text() else 0.0
            y_offset = float(self.bg_offset_y_input.text()) if self.bg_offset_y_input.text() else 0.0
            self.background_offset_changed.emit(x_offset, y_offset)
        except ValueError:
            # Invalid input, ignore
            pass
    
    def on_min_area_changed(self):
        """Handle minimum area changes"""
        try:
            min_area = float(self.min_area_input.text()) if self.min_area_input.text() else 30.0
            min_area = max(1.0, min_area)  # Ensure minimum value of 1.0
            self.min_area_changed.emit(min_area)
        except ValueError:
            # Invalid input, ignore
            pass
    
    def on_grid_toggled(self, checked):
        """Handle grid toggle"""
        self.grid_toggled.emit(checked)
    
    def on_grid_size_changed(self):
        """Handle grid size changes"""
        try:
            grid_size = int(self.grid_size_input.text()) if self.grid_size_input.text() else 400
            grid_size = max(10, grid_size)  # Ensure minimum grid size of 10
            self.grid_size_changed.emit(grid_size)
        except ValueError:
            # Invalid input, ignore
            pass
    
    def on_paint_toggled(self, checked):
        """Handle paint mode toggle"""
        self.paint_toggled.emit(checked)


class MosaicEditor(QMainWindow):
    """Main mosaic editor application"""
    
    def __init__(self):
        super().__init__()
        self.current_file = None
        self.setup_ui()
        self.connect_signals()
        
    def setup_ui(self):
        """Set up the main UI"""
        self.setWindowTitle("Mosaic Editor - Pure PyQt5")
        self.setFocusPolicy(Qt.StrongFocus)  # Ensure main window can receive key events
        
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout (vertical to accommodate color palette at bottom)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(5)
        main_layout.setContentsMargins(5, 5, 5, 5)
        
        # Top section layout (horizontal for canvas and control panel)
        top_layout = QHBoxLayout()
        top_layout.setSpacing(10)
        
        # Left status bar with buttons
        self.left_status_bar = QWidget()
        self.left_status_bar.setFixedWidth(200)
        self.left_status_bar.setStyleSheet("QWidget { background-color: #f0f0f0; border: 1px solid #ccc; }")
        self.left_status_bar.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        
        # Layout for left panel
        left_panel_layout = QVBoxLayout(self.left_status_bar)
        left_panel_layout.setContentsMargins(10, 10, 10, 10)
        
        # Background color button
        self.bg_color_btn = QPushButton("BG Color")
        self.bg_color_btn.setToolTip("Set background to selected color")
        left_panel_layout.addWidget(self.bg_color_btn)
        
        # Colorize button
        self.colorize_btn = QPushButton("Colorize")
        self.colorize_btn.setToolTip("Convert all tile colors to closest palette colors")
        left_panel_layout.addWidget(self.colorize_btn)
        
        # Choose Palette button
        self.choose_palette_btn = QPushButton("Choose Palette")
        self.choose_palette_btn.setToolTip("Choose a different color palette CSV file")
        left_panel_layout.addWidget(self.choose_palette_btn)
        
        # Reduce Colors button
        self.reduce_colors_btn = QPushButton("Reduce Colors")
        self.reduce_colors_btn.setToolTip("Reduce all tile colors to 16 dominant colors using OpenCV")
        left_panel_layout.addWidget(self.reduce_colors_btn)
        
        # Cut button
        self.cut_btn = QPushButton("Cut")
        self.cut_btn.setToolTip("Color tiles by grid box - each box gets a distinct color")
        left_panel_layout.addWidget(self.cut_btn)
        
        # Cut Plates button (initially disabled)
        self.cut_tiles_btn = QPushButton("Cut Plates")
        self.cut_tiles_btn.setToolTip("Fill each grid box with its assigned color and update tile frames")
        self.cut_tiles_btn.setEnabled(False)  # Disabled until Cut is used
        left_panel_layout.addWidget(self.cut_tiles_btn)
        
        # Save Boxes button
        self.save_boxes_btn = QPushButton("Save Boxes")
        self.save_boxes_btn.setToolTip("Save each grid box's polygons to separate CSV files")
        left_panel_layout.addWidget(self.save_boxes_btn)
        
        # Save Plates button
        self.save_plates_btn = QPushButton("Save Plates")
        self.save_plates_btn.setToolTip("Save detected blob contours as DXF files with frames")
        left_panel_layout.addWidget(self.save_plates_btn)
        
        # Overlap button
        self.overlap_btn = QPushButton("Overlap Check")
        self.overlap_btn.setToolTip("Highlight all polygon overlaps with red outlines")
        left_panel_layout.addWidget(self.overlap_btn)
        
        # Add stretch to push buttons to top
        left_panel_layout.addStretch()
        
        # Canvas with scale bars
        self.canvas_container = CanvasWithScaleBars()
        self.canvas_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        # Set reference to main editor for accessing selected color
        self.canvas_container.canvas.main_editor = self
        self.selected_palette_color = None  # Initialize selected color
        
        # Control panel - pass canvas reference
        self.control_panel = ControlPanel(canvas=self.canvas_container.canvas)
        self.control_panel.setFixedWidth(250)
        self.control_panel.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        
        # Add to top layout
        top_layout.addWidget(self.left_status_bar, 0)  # Left status bar fixed width
        top_layout.addWidget(self.canvas_container, 4)  # Canvas takes most space
        top_layout.addWidget(self.control_panel, 0)  # Control panel fixed width
        
        # Create color palette widget
        self.color_palette = ColorPaletteWidget()
        
        # Add to main layout
        main_layout.addLayout(top_layout, 1)  # Top section takes most space
        main_layout.addWidget(self.color_palette, 0)  # Color palette at bottom with fixed height
        
        # Maximize window after UI is fully set up
        self.showMaximized()
        
        # Give canvas focus so it can receive key events
        self.canvas_container.canvas.setFocus()
    
    def connect_signals(self):
        """Connect signals and slots"""
        # Control panel signals
        self.control_panel.load_btn.clicked.connect(self.load_file)
        self.control_panel.save_btn.clicked.connect(self.control_panel.save_visible_requested.emit)
        self.control_panel.load_image_btn.clicked.connect(self.control_panel.load_background_image)
        
        self.control_panel.edges_toggled.connect(self.on_edges_toggled)
        self.control_panel.edge_width_changed.connect(self.on_edge_width_changed)
        self.control_panel.transparent_toggled.connect(self.on_transparent_toggled)
        self.control_panel.eraser_toggled.connect(self.on_eraser_toggled)
        self.control_panel.polygon_toggled.connect(self.on_polygon_toggled)
        self.control_panel.background_image_loaded.connect(self.on_background_image_loaded)
        self.control_panel.background_offset_changed.connect(self.on_background_offset_changed)
        self.control_panel.background_visible_toggled.connect(self.on_background_visible_toggled)
        self.control_panel.min_area_changed.connect(self.on_min_area_changed)
        self.control_panel.grid_toggled.connect(self.on_grid_toggled)
        self.control_panel.grid_size_changed.connect(self.on_grid_size_changed)
        self.control_panel.paint_toggled.connect(self.on_paint_toggled)
        self.control_panel.save_visible_requested.connect(self.save_visible_array)
        
        # Left panel signals
        self.bg_color_btn.clicked.connect(self.on_bg_color_clicked)
        self.colorize_btn.clicked.connect(self.on_colorize_clicked)
        self.choose_palette_btn.clicked.connect(self.on_choose_palette_clicked)
        self.reduce_colors_btn.clicked.connect(self.on_reduce_colors_clicked)
        self.cut_btn.clicked.connect(self.on_cut_clicked)
        self.cut_tiles_btn.clicked.connect(self.on_cut_tiles_clicked)
        self.save_boxes_btn.clicked.connect(self.on_save_boxes_clicked)
        self.save_plates_btn.clicked.connect(self.on_save_plates_clicked)
        self.overlap_btn.clicked.connect(self.on_overlap_check_clicked)
        
        # Color palette signals
        self.color_palette.color_selected.connect(self.on_color_selected)
        
        # Initialize canvas with the palette's default selected color
        self.canvas_container.canvas.selected_palette_color = self.color_palette.selected_color
        
        # Set up statistics callback for canvas
        self.canvas_container.canvas.statistics_callback = self.update_statistics
    
    def update_statistics(self):
        """Update statistics display after changes"""
        if self.current_file and self.canvas_container.canvas.polygons:
            import os
            self.control_panel.update_stats(
                len(self.canvas_container.canvas.polygons), 
                os.path.basename(self.current_file)
            )
    
    def load_file(self):
        """Load a CSV file"""
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Load Mosaic CSV File",
            "",
            "CSV Files (*.csv);;All Files (*)"
        )
        
        if filename:
            if self.canvas_container.canvas.load_polygons_from_csv(filename):
                self.current_file = filename
                import os
                self.control_panel.update_stats(
                    len(self.canvas_container.canvas.polygons), 
                    os.path.basename(filename)
                )
                self.setWindowTitle(f"Mosaic Editor - {os.path.basename(filename)}")
                
                # Disable Cut Tiles button when loading new file (Cut operation data is now invalid)
                self.cut_tiles_btn.setEnabled(False)
                
                # Reset Cut Tiles applied flag when loading new file
                self.canvas_container.canvas.cut_tiles_applied = False
                
                # Update scale bars
                self.canvas_container.update_scale_bars()
    
    def on_edges_toggled(self, show_edges):
        """Handle edges checkbox toggle"""
        self.canvas_container.canvas.show_edges = show_edges
        self.canvas_container.canvas.invalidate_cache()
        self.canvas_container.canvas.update()
    
    def on_edge_width_changed(self, width):
        """Handle edge width change"""
        self.canvas_container.canvas.edge_width = width
        self.canvas_container.canvas.invalidate_cache()
        self.canvas_container.canvas.update()
    
    def on_transparent_toggled(self, transparent):
        """Handle transparent shapes toggle"""
        self.canvas_container.canvas.transparent_shapes = transparent
        self.canvas_container.canvas.invalidate_cache()
        self.canvas_container.canvas.update()
    
    def on_eraser_toggled(self, eraser_enabled):
        """Handle eraser mode toggle"""
        if eraser_enabled:
            # Disable other modes when enabling eraser
            self.control_panel.polygon_checkbox.setChecked(False)
            self.control_panel.paint_checkbox.setChecked(False)
        self.canvas_container.canvas.toggle_eraser_mode()
        # Update statistics after potential erasure
        if self.current_file and self.canvas_container.canvas.polygons:
            import os
            self.control_panel.update_stats(
                len(self.canvas_container.canvas.polygons), 
                os.path.basename(self.current_file)
            )
    
    def on_polygon_toggled(self, polygon_enabled):
        """Handle polygon mode toggle"""
        if polygon_enabled:
            # Disable other modes when enabling polygon mode
            self.control_panel.eraser_checkbox.setChecked(False)
            self.control_panel.paint_checkbox.setChecked(False)
        self.canvas_container.canvas.toggle_polygon_mode()
        # Update statistics after potential polygon creation
        if self.current_file and self.canvas_container.canvas.polygons:
            import os
            self.control_panel.update_stats(
                len(self.canvas_container.canvas.polygons), 
                os.path.basename(self.current_file)
            )
    
    def on_grid_toggled(self, show_grid):
        """Handle grid toggle"""
        self.canvas_container.canvas.show_grid = show_grid
        self.canvas_container.canvas.update()
    
    def on_grid_size_changed(self, grid_size):
        """Handle grid size change"""
        self.canvas_container.canvas.grid_size = grid_size
        if hasattr(self.canvas_container.canvas, 'show_grid') and self.canvas_container.canvas.show_grid:
            self.canvas_container.canvas.update()
    
    def on_paint_toggled(self, paint_enabled):
        """Handle paint mode toggle"""
        if paint_enabled:
            # Disable other modes when enabling paint mode
            self.control_panel.eraser_checkbox.setChecked(False)
            self.control_panel.polygon_checkbox.setChecked(False)
        self.canvas_container.canvas.toggle_paint_mode()
        
    def on_background_image_loaded(self, image_path):
        """Handle background image loading"""
        self.canvas_container.canvas.load_background_image(image_path)
        self.canvas_container.canvas.invalidate_cache()
        self.canvas_container.canvas.update()
    
    def on_background_offset_changed(self, x_offset, y_offset):
        """Handle background image offset changes"""
        self.canvas_container.canvas.background_offset_x = x_offset
        self.canvas_container.canvas.background_offset_y = y_offset
        self.canvas_container.canvas.invalidate_cache()
        self.canvas_container.canvas.update()
    
    def on_background_visible_toggled(self, visible):
        """Handle background image visibility toggle"""
        self.canvas_container.canvas.background_visible = visible
        self.canvas_container.canvas.invalidate_cache()
        self.canvas_container.canvas.update()
    
    def on_min_area_changed(self, min_area):
        """Handle minimum area changes"""
        self.canvas_container.canvas.min_area = min_area
        self.canvas_container.canvas.invalidate_cache()
        # Update visible polygons to account for new minimum area
        self.canvas_container.canvas.update_visible_polygons()
        self.canvas_container.canvas.update()
        
        # Update statistics to reflect the change
        if self.current_file and self.canvas_container.canvas.polygons:
            import os
            # Pass the total number of polygons and let update_stats filter by min_area
            self.control_panel.update_stats(
                len(self.canvas_container.canvas.polygons), 
                os.path.basename(self.current_file)
            )
        else:
            pass
    
    def on_bg_color_clicked(self):
        """Handle BG Color button click - set canvas background to selected palette color"""
        if hasattr(self, 'selected_palette_color') and self.selected_palette_color:
            self.canvas_container.canvas.canvas_background_color = self.selected_palette_color
            self.canvas_container.canvas.update()
    
    def on_colorize_clicked(self):
        """Handle Colorize button click - convert all tile colors to closest palette colors"""
        if not self.canvas_container.canvas.polygons:
            return
        
        # Get all colors from the palette
        palette_colors = self.color_palette.colors
        
        if not palette_colors:
            QMessageBox.warning(self, "Warning", "No palette colors available.")
            return
        
        # Count how many tiles will be processed
        total_tiles = len(self.canvas_container.canvas.colors)
        
        # Convert each tile color to closest palette color
        colors_changed = 0
        for i, current_color in enumerate(self.canvas_container.canvas.colors):
            closest_color = self.find_closest_palette_color(current_color, palette_colors)
            if closest_color != current_color:
                self.canvas_container.canvas.colors[i] = closest_color
                colors_changed += 1
        
        # Update the display
        self.canvas_container.canvas.invalidate_cache()
        self.canvas_container.canvas.update()
    
    def find_closest_palette_color(self, target_color, palette_colors):
        """Find the closest color in the palette to the target color"""
        if not palette_colors:
            return target_color
        
        # Calculate color distance using RGB values
        target_r, target_g, target_b = target_color.red(), target_color.green(), target_color.blue()
        
        closest_color = palette_colors[0]
        min_distance = float('inf')
        
        for palette_color in palette_colors:
            # Calculate Euclidean distance in RGB color space
            p_r, p_g, p_b = palette_color.red(), palette_color.green(), palette_color.blue()
            distance = ((target_r - p_r) ** 2 + (target_g - p_g) ** 2 + (target_b - p_b) ** 2) ** 0.5
            
            if distance < min_distance:
                min_distance = distance
                closest_color = palette_color
        
        return closest_color
    
    def on_choose_palette_clicked(self):
        """Handle Choose Palette button click - allow user to select a different CSV palette file"""
        from PyQt5.QtWidgets import QFileDialog
        
        # Open file dialog to choose CSV palette file
        csv_file, _ = QFileDialog.getOpenFileName(
            self,
            "Choose Color Palette CSV File",
            "",
            "CSV files (*.csv);;All files (*.*)"
        )
        
        if csv_file:
            # Try to load the new palette
            if self.color_palette.change_palette(csv_file):
                # Update the selected palette color to the first color in the new palette
                if self.color_palette.colors:
                    self.selected_palette_color = self.color_palette.colors[0]
                    self.color_palette.selected_color = self.selected_palette_color
                
                QMessageBox.information(
                    self,
                    "Palette Changed",
                    f"Successfully loaded palette from:\n{csv_file}\n\nColors loaded: {len(self.color_palette.colors)}"
                )
            else:
                QMessageBox.warning(
                    self,
                    "Error",
                    f"Failed to load palette from:\n{csv_file}\n\nPlease check that the file contains valid hex colors (e.g., #FF0000)"
                )
    
    def on_reduce_colors_clicked(self):
        """Handle Reduce Colors button click - reduce all tile colors to 16 dominant colors using OpenCV"""
        if not self.canvas_container.canvas.polygons:
            QMessageBox.information(self, "Info", "No tiles loaded to reduce colors.")
            return
        
        # Store original colors before reduction (for manufacturing DXF files)
        if not hasattr(self, 'original_colors') or len(self.original_colors) != len(self.canvas_container.canvas.colors):
            self.original_colors = self.canvas_container.canvas.colors.copy()
        
        try:
            import cv2
            import numpy as np
        except ImportError:
            QMessageBox.warning(
                self, 
                "OpenCV Required", 
                "OpenCV (cv2) is required for color reduction.\n\nPlease install it using:\npip install opencv-python"
            )
            return
        
        # Collect all tile colors
        colors_rgb = []
        valid_indices = []
        for i, color in enumerate(self.canvas_container.canvas.colors):
            if i < len(self.canvas_container.canvas.polygons):
                # Convert QColor to RGB
                colors_rgb.append([color.red(), color.green(), color.blue()])
                valid_indices.append(i)
        
        if not colors_rgb:
            QMessageBox.information(self, "Info", "No valid colors found to reduce.")
            return
        
        # Convert to numpy array
        colors_array = np.array(colors_rgb, dtype=np.float32)
        
        # Determine optimal number of clusters (max 16, but could be less if we have fewer unique colors)
        unique_colors = len(set(tuple(color) for color in colors_rgb))
        k = min(16, unique_colors)  # Don't cluster into more groups than we have unique colors
        
        if k == 1:
            QMessageBox.information(self, "Info", "All tiles already have the same color.")
            return
        criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 100, 0.2)
        attempts = 10
        
        # Perform K-means clustering
        _, labels, centers = cv2.kmeans(colors_array, k, None, criteria, attempts, cv2.KMEANS_RANDOM_CENTERS)
        
        # Convert cluster centers back to integers
        centers = np.uint8(centers)
        
        # Map each original color to its closest cluster center
        colors_changed = 0
        for idx, label in enumerate(labels.flatten()):
            tile_index = valid_indices[idx]  # Get the actual tile index
            if tile_index < len(self.canvas_container.canvas.colors):
                # Get the cluster center color for this tile
                new_rgb = centers[label]
                new_color = QColor(int(new_rgb[0]), int(new_rgb[1]), int(new_rgb[2]))
                
                # Check if color actually changed
                old_color = self.canvas_container.canvas.colors[tile_index]
                if old_color.rgb() != new_color.rgb():
                    colors_changed += 1
                
                # Update the tile color
                self.canvas_container.canvas.colors[tile_index] = new_color
        
        # Update the display
        self.canvas_container.canvas.invalidate_cache()
        self.canvas_container.canvas.update()
        
        # Update canvas display
        self.canvas_container.canvas.update()

    def on_cut_clicked(self):
        """Handle Cut button click - color tiles by grid box assignment"""
        if not self.canvas_container.canvas.polygons:
            return
        
        # Disable Cut button to prevent multiple simultaneous executions
        self.cut_btn.setEnabled(False)
        self.cut_btn.setText("Processing...")
        # Force UI update to show the disabled state immediately
        QApplication.processEvents()
        
        # Count how many tiles will be processed
        total_tiles = len(self.canvas_container.canvas.polygons)
        
        # Store current colors (which may have been modified by colorize/reduce colors) 
        # as the base colors for CSV files - this ensures colorize/reduce changes are preserved
        self.original_colors = self.canvas_container.canvas.colors.copy()
        
        # Define 36 distinct colors for the 6x6 grid (easy to distinguish)
        grid_colors = [
            QColor(255, 0, 0),     # Red
            QColor(0, 255, 0),     # Green  
            QColor(0, 0, 255),     # Blue
            QColor(255, 255, 0),   # Yellow
            QColor(255, 0, 255),   # Magenta
            QColor(0, 255, 255),   # Cyan
            QColor(255, 128, 0),   # Orange
            QColor(128, 0, 255),   # Purple
            QColor(0, 255, 128),   # Spring Green
            QColor(255, 0, 128),   # Rose
            QColor(128, 255, 0),   # Lime
            QColor(0, 128, 255),   # Sky Blue
            QColor(255, 64, 64),   # Light Red
            QColor(64, 255, 64),   # Light Green
            QColor(64, 64, 255),   # Light Blue
            QColor(255, 255, 128), # Light Yellow
            QColor(255, 128, 255), # Light Magenta
            QColor(128, 255, 255), # Light Cyan
            QColor(192, 0, 0),     # Dark Red
            QColor(0, 192, 0),     # Dark Green
            QColor(0, 0, 192),     # Dark Blue
            QColor(192, 192, 0),   # Dark Yellow
            QColor(192, 0, 192),   # Dark Magenta
            QColor(0, 192, 192),   # Dark Cyan
            QColor(255, 192, 128), # Peach
            QColor(192, 128, 255), # Lavender
            QColor(128, 255, 192), # Mint
            QColor(255, 128, 192), # Pink
            QColor(192, 255, 128), # Light Lime
            QColor(128, 192, 255), # Light Sky
            QColor(128, 128, 128), # Gray
            QColor(64, 64, 64),    # Dark Gray
            QColor(160, 160, 160), # Light Gray
            QColor(96, 96, 96),    # Medium Gray
            QColor(224, 224, 224), # Very Light Gray
            QColor(32, 32, 32)     # Very Dark Gray
        ]
        
        # Get grid parameters
        cell_size_world = self.canvas_container.canvas.grid_size
        grid_x_world = self.canvas_container.canvas.grid_offset_x
        grid_y_world = self.canvas_container.canvas.grid_offset_y
        
        tiles_assigned = 0
        
        # Track which grid boxes have polygons (for optimized blob detection)
        boxes_with_polygons = set()
        
        # Process each tile
        for i, polygon in enumerate(self.canvas_container.canvas.polygons):
            # Calculate which grid box this tile belongs to based on area overlap
            box_index = self.calculate_dominant_grid_box(polygon, grid_x_world, grid_y_world, cell_size_world)
            
            if box_index >= 0:  # Valid box assignment
                # Assign color based on grid box
                self.canvas_container.canvas.colors[i] = grid_colors[box_index % len(grid_colors)]
                boxes_with_polygons.add(box_index)  # Track boxes with polygons
                tiles_assigned += 1
        
        # Store boxes with polygons for Cut Plates optimization
        self.canvas_container.canvas.boxes_with_polygons = boxes_with_polygons
        
        # Update the display
        self.canvas_container.canvas.invalidate_cache()
        self.canvas_container.canvas.update()
        
        # Enable Cut Tiles button after Cut operation
        self.cut_tiles_btn.setEnabled(True)
        
        # Re-enable Cut button after operation is complete
        self.cut_btn.setEnabled(True)
        self.cut_btn.setText("Cut")
        # Force UI update to show the re-enabled state
        QApplication.processEvents()
    
    def calculate_dominant_grid_box(self, polygon, grid_x, grid_y, cell_size):
        """Calculate which grid box contains most of the polygon's area"""
        from shapely.geometry import Polygon as ShapelyPolygon, box
        
        # The polygon is already a Shapely polygon
        try:
            if not polygon.is_valid:
                return -1
        except:
            return -1
        
        max_overlap_area = 0
        best_box_index = -1
        
        # Check overlap with each of the 36 grid boxes (6x6)
        for row in range(6):
            for col in range(6):
                # Calculate box bounds
                box_x1 = grid_x + col * cell_size
                box_y1 = grid_y + row * cell_size
                box_x2 = box_x1 + cell_size
                box_y2 = box_y1 + cell_size
                
                # Create box geometry
                grid_box = box(box_x1, box_y1, box_x2, box_y2)
                
                try:
                    # Calculate intersection area
                    intersection = polygon.intersection(grid_box)
                    overlap_area = intersection.area
                    
                    if overlap_area > max_overlap_area:
                        max_overlap_area = overlap_area
                        best_box_index = row * 6 + col  # Convert 2D index to 1D
                except:
                    continue
        
        return best_box_index
    
    def on_cut_tiles_clicked(self):
        """Handle Cut Tiles button click - fill each grid box with its assigned color and update tile frames"""
        if not self.canvas_container.canvas.polygons:
            return
        
        # Disable Cut Plates button to prevent multiple simultaneous executions
        self.cut_tiles_btn.setEnabled(False)
        self.cut_tiles_btn.setText("Processing...")
        # Force UI update to show the disabled state immediately
        QApplication.processEvents()
        
        # Get grid parameters
        cell_size_world = self.canvas_container.canvas.grid_size
        grid_x_world = self.canvas_container.canvas.grid_offset_x
        grid_y_world = self.canvas_container.canvas.grid_offset_y
        
        # Define 36 rainbow colors with maximum distinction for better OpenCV detection
        grid_colors = [
            QColor(255, 0, 0),     # Pure Red
            QColor(255, 165, 0),   # Orange  
            QColor(255, 255, 0),   # Yellow
            QColor(128, 255, 0),   # Yellow-Green
            QColor(0, 255, 0),     # Pure Green
            QColor(0, 255, 128),   # Green-Cyan
            QColor(0, 255, 255),   # Cyan
            QColor(0, 128, 255),   # Light Blue
            QColor(0, 0, 255),     # Pure Blue
            QColor(128, 0, 255),   # Blue-Violet
            QColor(255, 0, 255),   # Magenta
            QColor(255, 0, 128),   # Pink
            QColor(128, 0, 0),     # Dark Red
            QColor(128, 82, 0),    # Dark Orange
            QColor(128, 128, 0),   # Dark Yellow/Olive
            QColor(64, 128, 0),    # Dark Yellow-Green
            QColor(0, 128, 0),     # Dark Green
            QColor(0, 128, 64),    # Dark Green-Cyan
            QColor(0, 128, 128),   # Dark Cyan/Teal
            QColor(0, 64, 128),    # Dark Light Blue
            QColor(0, 0, 128),     # Dark Blue/Navy
            QColor(64, 0, 128),    # Dark Violet
            QColor(128, 0, 128),   # Dark Magenta
            QColor(128, 0, 64),    # Dark Pink
            QColor(255, 128, 128), # Light Red
            QColor(255, 192, 128), # Light Orange
            QColor(255, 255, 128), # Light Yellow
            QColor(192, 255, 128), # Light Yellow-Green
            QColor(128, 255, 128), # Light Green
            QColor(128, 255, 192), # Light Green-Cyan
            QColor(128, 255, 255), # Light Cyan
            QColor(128, 192, 255), # Light Blue
            QColor(128, 128, 255), # Light Blue-Purple
            QColor(192, 128, 255), # Light Violet
            QColor(255, 128, 255), # Light Magenta
            QColor(255, 128, 192)  # Light Pink
        ]
        
        tiles_processed = 0
        
        # Process each tile
        for i, polygon in enumerate(self.canvas_container.canvas.polygons):
            # Calculate which grid box this tile belongs to
            box_index = self.calculate_dominant_grid_box(polygon, grid_x_world, grid_y_world, cell_size_world)
            
            if box_index >= 0:  # Valid box assignment
                # Get the assigned color for this box
                assigned_color = grid_colors[box_index % len(grid_colors)]
                
                # Update both fill color and frame color to match the box color
                if i < len(self.canvas_container.canvas.colors):
                    self.canvas_container.canvas.colors[i] = assigned_color
                
                if i < len(self.canvas_container.canvas.edge_colors):
                    self.canvas_container.canvas.edge_colors[i] = assigned_color
                
                tiles_processed += 1
        
        # Update the display
        self.canvas_container.canvas.invalidate_cache()
        self.canvas_container.canvas.update()
        
        # Set flag to indicate Cut Tiles has been applied (for grid box fill colors)
        self.canvas_container.canvas.cut_tiles_applied = True
        
        # Save DXF files for grid box perimeters
        self.save_box_tiles()
        
        # Re-enable Cut Plates button after operation is complete
        self.cut_tiles_btn.setEnabled(True)
        self.cut_tiles_btn.setText("Cut Plates")
        # Force UI update to show the re-enabled state
        QApplication.processEvents()

    def on_save_boxes_clicked(self):
        """Handle Save Boxes button click - save each grid box's polygons to separate CSV files"""
        if not self.canvas_container.canvas.polygons:
            QMessageBox.information(self, "Info", "No tiles loaded to save.")
            return
        
        # Disable Save Boxes button to prevent multiple simultaneous executions
        self.save_boxes_btn.setEnabled(False)
        self.save_boxes_btn.setText("Processing...")
        # Force UI update to show the disabled state immediately
        QApplication.processEvents()
        
        # Let user choose the output folder
        folder_path = QFileDialog.getExistingDirectory(
            self, 
            "Choose Folder to Save Grid Box CSV Files",
            "",
            QFileDialog.ShowDirsOnly | QFileDialog.DontResolveSymlinks
        )
        
        if not folder_path:
            # Re-enable button if user cancels
            self.save_boxes_btn.setEnabled(True)
            self.save_boxes_btn.setText("Save Boxes")
            return  # User cancelled
        
        # Ask user if they want to apply filet to polygons
        from PyQt5.QtWidgets import QMessageBox
        reply = QMessageBox.question(
            self,
            "Apply Filet",
            "Do you want to apply filet (radius 0.5) to all polygon corners in the DXF files?\n\n"
            "This will create rounded corners on the tiles.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No  # Default to No
        )
        
        apply_filet = (reply == QMessageBox.Yes)
        
        # Get grid parameters
        cell_size_world = self.canvas_container.canvas.grid_size
        grid_x_world = self.canvas_container.canvas.grid_offset_x
        grid_y_world = self.canvas_container.canvas.grid_offset_y
        
        # Initialize original colors if not available (in case Cut wasn't used)
        if not hasattr(self, 'original_colors') or len(self.original_colors) != len(self.canvas_container.canvas.colors):
            self.original_colors = self.canvas_container.canvas.colors.copy()
        
        # Dictionary to store polygons for each grid box
        box_polygons = {}
        tiles_processed = 0
        tiles_assigned = 0
        
        # Process each tile and assign to grid boxes
        for i, polygon in enumerate(self.canvas_container.canvas.polygons):
            tiles_processed += 1
            
            # Calculate which grid box this tile belongs to
            box_index = self.calculate_dominant_grid_box(polygon, grid_x_world, grid_y_world, cell_size_world)
            
            if box_index >= 0:  # Valid box assignment
                if box_index not in box_polygons:
                    box_polygons[box_index] = []
                
                # Store polygon with its color
                color = self.canvas_container.canvas.colors[i] if i < len(self.canvas_container.canvas.colors) else QColor(0, 0, 0)
                
                # Get original color if available (for manufacturing DXF files)
                original_color = color  # Default to current color
                if hasattr(self, 'original_colors') and i < len(self.original_colors):
                    original_color = self.original_colors[i]
                
                box_polygons[box_index].append({
                    'polygon': polygon,
                    'color': color,
                    'original_color': original_color,
                    'original_index': i
                })
                tiles_assigned += 1
        
        # Save CSV files and DXF files for each grid box
        files_saved = 0
        dxf_files_saved = 0
        folders_created = 0
        
        for box_index, polygons_data in box_polygons.items():
            # Convert box index to row/column (A1, A2, etc.)
            row = box_index // 6
            col = box_index % 6
            box_name = f"{chr(ord('A') + row)}{col + 1}"
            
            # Create folder for this box
            box_folder_path = f"{folder_path}/{box_name}"
            try:
                import os
                os.makedirs(box_folder_path, exist_ok=True)
                folders_created += 1
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Failed to create folder {box_name}: {str(e)}")
                continue
            
            # Create filenames in the box folder
            csv_filename = f"box_{box_name}.csv"
            dxf_filename = f"box_{box_name}.dxf"
            csv_filepath = f"{box_folder_path}/{csv_filename}"
            dxf_filepath = f"{box_folder_path}/{dxf_filename}"
            
            # Save CSV file
            try:
                with open(csv_filepath, 'w', newline='', encoding='utf-8') as csvfile:
                    import csv
                    import json
                    
                    writer = csv.writer(csvfile)
                    
                    # Write header (same format as save_visible_array)
                    writer.writerow(['polygon_id', 'coordinates', 'color_r', 'color_g', 'color_b', 'color_a'])
                    
                    # Write each polygon
                    for poly_id, poly_data in enumerate(polygons_data):
                        polygon = poly_data['polygon']
                        # Use original color (before Cut operation) for CSV files
                        original_color = poly_data.get('original_color', poly_data['color'])
                        
                        # Extract coordinates as a list of [x, y] pairs (same format as save_visible_array)
                        coords = list(polygon.exterior.coords)
                        coords_json = json.dumps([[float(x), float(y)] for x, y in coords])
                        
                        # Extract RGBA values (convert from QColor to 0-1 range, same as save_visible_array)
                        r = original_color.red() / 255.0
                        g = original_color.green() / 255.0
                        b = original_color.blue() / 255.0
                        a = original_color.alpha() / 255.0
                        
                        # Write row
                        writer.writerow([poly_id, coords_json, r, g, b, a])
                
                files_saved += 1
                
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Failed to save CSV {csv_filename}: {str(e)}")
                continue
            
            # Save DXF files - main box file and separate files for each color
            try:
                # Save main DXF file with all polygons
                self.save_polygons_to_dxf(polygons_data, dxf_filepath, box_name, box_index, apply_filet)
                dxf_files_saved += 1
                
                # Group polygons by original color (for manufacturing accuracy)
                color_groups = {}
                for poly_data in polygons_data:
                    original_color = poly_data.get('original_color', poly_data['color'])
                    color_hex = original_color.name()  # Get hex color like #FF0000
                    
                    if color_hex not in color_groups:
                        color_groups[color_hex] = []
                    
                    # Use original color for the DXF file
                    poly_data_copy = poly_data.copy()
                    poly_data_copy['color'] = original_color
                    color_groups[color_hex].append(poly_data_copy)
                
                # Save separate DXF file for each color
                for color_hex, color_polygons in color_groups.items():
                    color_dxf_filename = f"{box_name}_{color_hex}.dxf"
                    color_dxf_filepath = f"{box_folder_path}/{color_dxf_filename}"
                    
                    try:
                        self.save_polygons_to_dxf(color_polygons, color_dxf_filepath, f"{box_name} - {color_hex}", box_index, apply_filet)
                        dxf_files_saved += 1
                    except Exception as e:
                        QMessageBox.warning(self, "Error", f"Failed to save color DXF {color_dxf_filename}: {str(e)}")
                        continue
                
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Failed to save DXF {dxf_filename}: {str(e)}")
                continue
        
        # Create general CSV file with all polygons and color area summary
        try:
            general_csv_path = f"{folder_path}/all_polygons_general.csv"
            color_areas = {}  # Dictionary to store total area for each color
            
            with open(general_csv_path, 'w', newline='', encoding='utf-8') as csvfile:
                import csv
                import json
                
                writer = csv.writer(csvfile)
                
                # Write header
                writer.writerow(['polygon_id', 'box_name', 'coordinates', 'color_r', 'color_g', 'color_b', 'color_a', 'area'])
                
                # Write all polygons from all boxes
                global_polygon_id = 0
                for box_index, polygons_data in box_polygons.items():
                    # Convert box index to row/column (A1, A2, etc.)
                    row = box_index // 6
                    col = box_index % 6
                    box_name = f"{chr(ord('A') + row)}{col + 1}"
                    
                    for poly_data in polygons_data:
                        polygon = poly_data['polygon']
                        original_color = poly_data.get('original_color', poly_data['color'])
                        
                        # Calculate area
                        poly_area = polygon.area
                        
                        # Track color areas
                        color_key = original_color.name()  # Get hex color like #FF0000
                        if color_key not in color_areas:
                            color_areas[color_key] = 0
                        color_areas[color_key] += poly_area
                        
                        # Extract coordinates
                        coords = list(polygon.exterior.coords)
                        coords_json = json.dumps([[float(x), float(y)] for x, y in coords])
                        
                        # Extract RGBA values
                        r = original_color.red() / 255.0
                        g = original_color.green() / 255.0
                        b = original_color.blue() / 255.0
                        a = original_color.alpha() / 255.0
                        
                        # Write polygon row
                        writer.writerow([global_polygon_id, box_name, coords_json, r, g, b, a, poly_area])
                        global_polygon_id += 1
                
                # Add separator and color area summary
                writer.writerow([])  # Empty row
                writer.writerow(['COLOR AREA SUMMARY'])
                writer.writerow(['Color (Hex)', 'Total Area'])
                
                # Sort colors by total area (descending)
                sorted_colors = sorted(color_areas.items(), key=lambda x: x[1], reverse=True)
                
                for color_hex, total_area in sorted_colors:
                    writer.writerow([color_hex, total_area])
                
                # Add total area of all polygons
                total_all_areas = sum(color_areas.values())
                writer.writerow([])  # Empty row
                writer.writerow(['TOTAL AREA (ALL COLORS)', total_all_areas])
            
            files_saved += 1
            
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to save general CSV file: {str(e)}")
        
        # Show completion message
        QMessageBox.information(
            self, 
            "Save Complete", 
            f"Successfully saved:\n"
            f"• {folders_created} grid box folders\n"
            f"• {files_saved} CSV files (including general file)\n"
            f"• {dxf_files_saved} DXF files\n"
            f"• Processed {tiles_processed} tiles, assigned {tiles_assigned} to boxes"
        )
        
        # Re-enable Save Boxes button after operation is complete
        self.save_boxes_btn.setEnabled(True)
        self.save_boxes_btn.setText("Save Boxes")
        # Force UI update to show the re-enabled state
        QApplication.processEvents()

    def save_polygons_to_dxf(self, polygons_data, dxf_filepath, box_name, box_index=None, apply_filet=False):
        """Save polygons to DXF file format with frame based on grid box dimensions"""
        # Create a simple DXF file manually (without external dependencies)
        with open(dxf_filepath, 'w', encoding='utf-8') as f:
            # DXF header
            f.write("0\nSECTION\n2\nHEADER\n9\n$ACADVER\n1\nAC1015\n0\nENDSEC\n")
            
            # Tables section
            f.write("0\nSECTION\n2\nTABLES\n")
            
            # Layer table
            f.write("0\nTABLE\n2\nLAYER\n70\n1\n")
            f.write("0\nLAYER\n2\n0\n70\n0\n6\nCONTINUOUS\n62\n7\n")
            f.write("0\nENDTAB\n")
            
            f.write("0\nENDSEC\n")
            
            # Entities section
            f.write("0\nSECTION\n2\nENTITIES\n")
            
            # Add title text
            f.write(f"0\nTEXT\n8\n0\n10\n0.0\n20\n0.0\n30\n0.0\n40\n10.0\n1\nGrid Box {box_name}\n")
            
            # Calculate frame based on grid box dimensions + 20 pixel margin
            if box_index is not None:
                # Get grid parameters
                cell_size_world = self.canvas_container.canvas.grid_size
                grid_x_world = self.canvas_container.canvas.grid_offset_x
                grid_y_world = self.canvas_container.canvas.grid_offset_y
                
                # Calculate grid box position
                row = box_index // 6
                col = box_index % 6
                
                # Calculate original grid box bounds
                box_min_x = grid_x_world + col * cell_size_world
                box_min_y = grid_y_world + row * cell_size_world
                box_max_x = box_min_x + cell_size_world
                box_max_y = box_min_y + cell_size_world
                
                # Add 20 pixels margin on each side for the frame
                frame_margin = 20
                frame_min_x = box_min_x - frame_margin
                frame_min_y = box_min_y - frame_margin
                frame_max_x = box_max_x + frame_margin
                frame_max_y = box_max_y + frame_margin
                
            elif polygons_data:
                # Fallback: calculate from polygons if box_index not provided
                min_x = float('inf')
                min_y = float('inf')
                max_x = float('-inf')
                max_y = float('-inf')
                
                # Find bounds of all polygons
                for poly_data in polygons_data:
                    polygon = poly_data['polygon']
                    bounds = polygon.bounds  # (minx, miny, maxx, maxy)
                    min_x = min(min_x, bounds[0])
                    min_y = min(min_y, bounds[1])
                    max_x = max(max_x, bounds[2])
                    max_y = max(max_y, bounds[3])
                
                # Add 20 pixels margin on each side for the frame
                frame_margin = 20
                frame_min_x = min_x - frame_margin
                frame_min_y = min_y - frame_margin
                frame_max_x = max_x + frame_margin
                frame_max_y = max_y + frame_margin
            else:
                # No frame if no data
                frame_min_x = frame_min_y = frame_max_x = frame_max_y = 0
            
            # Draw frame as a rectangle (LWPOLYLINE) if we have valid frame dimensions
            if (box_index is not None) or polygons_data:
                f.write("0\nLWPOLYLINE\n")
                f.write("8\n0\n")  # Layer
                f.write("62\n8\n")  # Color (dark gray for frame)
                f.write("90\n4\n")  # 4 vertices for rectangle
                f.write("70\n1\n")  # Closed polyline
                
                # Write frame vertices (clockwise from bottom-left)
                f.write(f"10\n{frame_min_x:.6f}\n20\n{frame_min_y:.6f}\n")  # Bottom-left
                f.write(f"10\n{frame_max_x:.6f}\n20\n{frame_min_y:.6f}\n")  # Bottom-right
                f.write(f"10\n{frame_max_x:.6f}\n20\n{frame_max_y:.6f}\n")  # Top-right
                f.write(f"10\n{frame_min_x:.6f}\n20\n{frame_max_y:.6f}\n")  # Top-left
            
            # Write each polygon as a POLYLINE
            for poly_id, poly_data in enumerate(polygons_data):
                polygon = poly_data['polygon']
                color = poly_data['color']
                
                # Apply filet if requested
                if apply_filet:
                    try:
                        # Apply internal filet with radius 0.5
                        filet_radius = 0.5
                        
                        # Create internal filet that doesn't exceed original polygon boundaries
                        shrunk_polygon = polygon.buffer(-filet_radius)
                        
                        if shrunk_polygon.is_valid and not shrunk_polygon.is_empty:
                            # Expand back by same radius to create rounded corners
                            filleted_polygon = shrunk_polygon.buffer(filet_radius)
                            
                            # Ensure result doesn't exceed original boundaries by intersecting
                            final_polygon = filleted_polygon.intersection(polygon)
                            
                            # Handle MultiPolygon results (take the largest polygon)
                            from shapely.geometry import MultiPolygon
                            if isinstance(final_polygon, MultiPolygon):
                                if len(final_polygon.geoms) > 0:
                                    final_polygon = max(final_polygon.geoms, key=lambda p: p.area)
                                else:
                                    final_polygon = polygon  # Fallback to original
                            
                            # Use filleted polygon if valid
                            if (final_polygon.is_valid and 
                                not final_polygon.is_empty and 
                                hasattr(final_polygon, 'exterior')):
                                polygon = final_polygon
                    
                    except Exception as e:
                        # If filet fails, use original polygon
                        print(f"Warning: Could not apply filet to polygon {poly_id}: {e}")
                
                # Get coordinates from the (possibly filleted) polygon
                coords = list(polygon.exterior.coords)
                
                # Map color to AutoCAD color index (simplified)
                color_index = self.get_autocad_color_index(color)
                
                # Start POLYLINE entity
                f.write("0\nLWPOLYLINE\n")
                f.write("8\n0\n")  # Layer
                f.write(f"62\n{color_index}\n")  # Color
                f.write(f"90\n{len(coords)-1}\n")  # Number of vertices (exclude duplicate last point)
                f.write("70\n1\n")  # Closed polyline
                
                # Write vertices (skip the last duplicate point)
                for x, y in coords[:-1]:
                    f.write(f"10\n{float(x):.6f}\n")  # X coordinate
                    f.write(f"20\n{float(y):.6f}\n")  # Y coordinate
            
            # End entities section
            f.write("0\nENDSEC\n")
            
            # End of file
            f.write("0\nEOF\n")
    
    def get_autocad_color_index(self, qcolor):
        """Convert QColor to nearest AutoCAD color index (1-255)"""
        # Simple color mapping to common AutoCAD colors
        r, g, b = qcolor.red(), qcolor.green(), qcolor.blue()
        
        # Basic color mapping
        if r > 200 and g < 100 and b < 100:
            return 1  # Red
        elif r < 100 and g > 200 and b < 100:
            return 3  # Green
        elif r < 100 and g < 100 and b > 200:
            return 5  # Blue
        elif r > 200 and g > 200 and b < 100:
            return 2  # Yellow
        elif r > 200 and g < 100 and b > 200:
            return 6  # Magenta
        elif r < 100 and g > 200 and b > 200:
            return 4  # Cyan
        elif r < 100 and g < 100 and b < 100:
            return 8  # Dark gray
        elif r > 200 and g > 200 and b > 200:
            return 7  # White
        else:
            return 9  # Light gray (default)
    
    def on_color_selected(self, color):
        """Handle color selection from the palette"""
        # Store the selected color locally and pass it to the canvas
        self.selected_palette_color = color
        # Update the canvas with the selected color for paint mode
        self.canvas_container.canvas.selected_palette_color = color
    
    def keyPressEvent(self, event):
        """Handle global keyboard shortcuts"""
        if event.key() == Qt.Key_Escape:
            # Exit all modes and return to normal cursor
            self.exit_all_modes()
        elif event.key() == Qt.Key_P:
            # Toggle polygon mode with 'p' key - simulate actual checkbox click
            self.control_panel.polygon_checkbox.click()
        elif event.key() == Qt.Key_E:
            # Toggle eraser mode with 'e' key - simulate actual checkbox click
            self.control_panel.eraser_checkbox.click()
        elif event.key() == Qt.Key_B:
            # Toggle paint mode with 'b' key (for brush) - simulate actual checkbox click
            self.control_panel.paint_checkbox.click()
        else:
            super().keyPressEvent(event)
    
    def exit_all_modes(self):
        """Exit all special modes (paint, eraser, polygon) and return to normal cursor"""
        try:
            canvas = self.canvas_container.canvas
            
            # Disable all modes by unchecking their checkboxes
            if hasattr(self.control_panel, 'paint_checkbox') and self.control_panel.paint_checkbox.isChecked():
                self.control_panel.paint_checkbox.setChecked(False)
            
            if hasattr(self.control_panel, 'eraser_checkbox') and self.control_panel.eraser_checkbox.isChecked():
                self.control_panel.eraser_checkbox.setChecked(False)
            
            if hasattr(self.control_panel, 'polygon_checkbox') and self.control_panel.polygon_checkbox.isChecked():
                self.control_panel.polygon_checkbox.setChecked(False)
            
            # Reset canvas mode variables
            if hasattr(canvas, 'paint_mode'):
                canvas.paint_mode = False
            if hasattr(canvas, 'eraser_mode'):
                canvas.eraser_mode = False
            if hasattr(canvas, 'polygon_mode'):
                canvas.polygon_mode = False
            
            # Ensure canvas returns to normal cursor
            canvas.setCursor(Qt.ArrowCursor)
            
            # Reset any ongoing operations
            if hasattr(canvas, 'polygon_points'):
                canvas.polygon_points = []
            
            if hasattr(canvas, 'is_painting'):
                canvas.is_painting = False
                
            if hasattr(canvas, 'last_painted_polygon'):
                canvas.last_painted_polygon = None
            
            if hasattr(canvas, 'is_erasing'):
                canvas.is_erasing = False
            
            # Force canvas update
            canvas.update()
            
        except Exception as e:
            # Silently handle any errors to prevent crashes
            print(f"Warning: Error in exit_all_modes: {e}")

    def save_box_tiles(self):
        """Detect blobs only in grid boxes that contain polygons (from Cut operation)."""
        try:
            canvas = self.canvas_container.canvas
            
            # Check if Cut Tiles has been applied
            if not hasattr(canvas, 'cut_tiles_applied') or not canvas.cut_tiles_applied:
                print("Cut Tiles must be applied first")
                return
            
            # Check if Cut has been run to identify boxes with polygons
            if not hasattr(canvas, 'boxes_with_polygons'):
                print("Cut must be run first to identify boxes with polygons")
                return
                
            boxes_to_process = canvas.boxes_with_polygons
            box_labels = [f"{chr(ord('A') + (i//6))}{(i%6)+1}" for i in sorted(boxes_to_process)]
            print(f"Detecting blobs in {len(boxes_to_process)} boxes that contain polygons: {', '.join(box_labels)}")
            
            # Initialize storage for all contours
            canvas.all_contours = {}  # Dictionary mapping box_index to contours list
            
            # Calculate grid parameters
            cell_size_world = canvas.grid_size
            grid_x_world = canvas.grid_offset_x
            grid_y_world = canvas.grid_offset_y
            margin = 20
            
            # Grid labels for debugging (A1-F6)
            rows = ['A', 'B', 'C', 'D', 'E', 'F']
            cols = ['1', '2', '3', '4', '5', '6']
            
            # Process only boxes that contain polygons
            total_contours_found = 0
            for box_index in boxes_to_process:
                # Calculate row and column from box index (0-35)
                row = box_index // 6  # 0-5
                col = box_index % 6   # 0-5
                box_label = f"{rows[row]}{cols[col]}"
                
                # Calculate box boundaries in world coordinates
                box_left = grid_x_world + (col * cell_size_world)
                box_top = grid_y_world + (row * cell_size_world)
                box_right = box_left + cell_size_world
                box_bottom = box_top + cell_size_world
                
                # Convert to screen coordinates
                screen_left, screen_top = canvas.world_to_screen(box_left, box_top)
                screen_right, screen_bottom = canvas.world_to_screen(box_right, box_bottom)
                
                # Calculate screen rectangle with margins
                screen_x = int(min(screen_left, screen_right)) - margin
                screen_y = int(min(screen_top, screen_bottom)) - margin
                screen_width = int(abs(screen_right - screen_left)) + 2 * margin
                screen_height = int(abs(screen_bottom - screen_top)) + 2 * margin
                
                # Capture the box area with margins
                box_rect = QRect(screen_x, screen_y, screen_width, screen_height)
                box_pixmap = canvas.grab(box_rect)
                
                # Save debug image for first few boxes
                if box_index < 3:  # Save A1, A2, A3 for inspection
                    box_pixmap.save(f"debug_{box_label.lower()}_capture.png")
                    print(f"Saved debug_{box_label.lower()}_capture.png for inspection")
            
                # Save debug image for first few boxes
                if box_index < 3:  # Save A1, A2, A3 for inspection
                    box_pixmap.save(f"debug_{box_label.lower()}_capture.png")
                    print(f"Saved debug_{box_label.lower()}_capture.png for inspection")
                
                # Convert to OpenCV format for analysis
                qimage = box_pixmap.toImage()
                width = qimage.width()
                height = qimage.height()
                
                # Check if the image is valid
                if width == 0 or height == 0:
                    print(f"Invalid image size for {box_label}: {width}x{height}")
                    canvas.all_contours[box_index] = []
                    continue
                
                # Convert to numpy array (RGBA format)
                ptr = qimage.bits()
                if ptr is None:
                    print(f"Failed to get image data for {box_label}")
                    canvas.all_contours[box_index] = []
                    continue
                    
                ptr.setsize(height * width * 4)
                arr = np.frombuffer(ptr, np.uint8).reshape((height, width, 4))
                
                # Convert RGBA to BGR for OpenCV
                bgr_image = cv2.cvtColor(arr, cv2.COLOR_RGBA2BGR)
                
                # Save BGR version for first few boxes
                if box_index < 3:
                    cv2.imwrite(f"debug_{box_label.lower()}_bgr.png", bgr_image)
                
                # Sample the center color of the box (accounting for margins)
                center_x = width // 2
                center_y = height // 2
                
                if center_x < width and center_y < height:
                    bgr_center = bgr_image[center_y, center_x]
                    
                    # Use the center color for detection
                    target_color = QColor(int(bgr_center[2]), int(bgr_center[1]), int(bgr_center[0]))
                    
                    # Perform blob detection on the captured area
                    contours = self.detect_blob(bgr_image, target_color, tolerance=30)
                    
                    if contours:
                        print(f"Found {len(contours)} contour(s) in {box_label}")
                        total_contours_found += len(contours)
                        
                        # Convert contours to world coordinates
                        world_contours = []
                        for contour in contours:
                            world_contour = []
                            for point in contour:
                                px, py = point[0]
                                # Convert from captured image coordinates to screen coordinates
                                screen_px = px + screen_x + 1  # Add 1 pixel offset to the right
                                screen_py = py + screen_y + 1  # Add 1 pixel offset down
                                # Convert to world coordinates
                                world_x, world_y = canvas.screen_to_world(screen_px, screen_py)
                                world_contour.append([world_x, world_y])
                            
                            world_contours.append(world_contour)
                        
                        # Store contours for this box
                        canvas.all_contours[box_index] = world_contours
                    else:
                        # No contours found for this box
                        canvas.all_contours[box_index] = []
                else:
                    canvas.all_contours[box_index] = []
            
            print(f"Detection completed. Found total of {total_contours_found} contours across all boxes.")
            canvas.update()  # Refresh display to show all contours
            
        except Exception as e:
            print(f"Error in blob detection: {e}")
            import traceback
            traceback.print_exc()

    def on_save_plates_clicked(self):
        """Handle Save Plates button click - save detected blob contours as DXF files with frames"""
        canvas = self.canvas_container.canvas
        
        # Check if blob detection has been performed
        if not hasattr(canvas, 'all_contours') or not canvas.all_contours:
            QMessageBox.information(self, "Info", "No blob contours detected. Please run 'Cut Plates' first.")
            return
        
        # Let user choose the output folder
        folder_path = QFileDialog.getExistingDirectory(
            self, 
            "Choose Folder to Save DXF Plate Files",
            "",
            QFileDialog.ShowDirsOnly | QFileDialog.DontResolveSymlinks
        )
        
        if not folder_path:
            return  # User cancelled
        
        try:
            # Grid labels for file naming (A1-F6)
            rows = ['A', 'B', 'C', 'D', 'E', 'F']
            cols = ['1', '2', '3', '4', '5', '6']
            
            # Get grid parameters for frame calculation
            cell_size_world = canvas.grid_size
            grid_x_world = canvas.grid_offset_x
            grid_y_world = canvas.grid_offset_y
            margin = 13  # 15 pixel margin for frame
            
            files_saved = 0
            
            for box_index, contours in canvas.all_contours.items():
                if not contours:
                    continue  # Skip boxes with no contours
                
                # Calculate grid box name
                row = box_index // 6  # 0-5
                col = box_index % 6   # 0-5
                box_label = f"{rows[row]}{cols[col]}"
                
                # Calculate box boundaries in world coordinates for frame
                box_left = grid_x_world + (col * cell_size_world)
                box_top = grid_y_world + (row * cell_size_world)
                box_right = box_left + cell_size_world
                box_bottom = box_top + cell_size_world
                
                # Use same fixed 20-pixel margin as Save Boxes for consistency
                world_margin = 20  # Fixed 20 pixel margin in world coordinates
                
                # Create frame coordinates with margin
                frame_left = box_left - world_margin
                frame_top = box_top - world_margin
                frame_right = box_right + world_margin
                frame_bottom = box_bottom + world_margin
                
                # Create DXF file path
                dxf_filename = f"{box_label}.dxf"
                dxf_filepath = f"{folder_path}/{dxf_filename}"
                
                # Save contours and frame to DXF
                try:
                    self.save_contours_and_frame_to_dxf(contours, frame_left, frame_top, frame_right, frame_bottom, dxf_filepath, box_label)
                    files_saved += 1
                    print(f"Saved {dxf_filename}")
                except Exception as e:
                    print(f"Error saving {dxf_filename}: {e}")
                    QMessageBox.warning(self, "Error", f"Failed to save {dxf_filename}: {str(e)}")
            
            # Show completion message
            QMessageBox.information(self, "Export Complete", f"Saved {files_saved} DXF plate files to:\n{folder_path}")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"An error occurred while saving plates: {str(e)}")

    def save_contours_and_frame_to_dxf(self, contours, frame_left, frame_top, frame_right, frame_bottom, dxf_path, box_label):
        """Save contours and 3 circles arranged in pyramid pattern to a DXF file (no frame)"""
        try:
            import ezdxf
            
            # Create new DXF document
            doc = ezdxf.new('R2010')
            msp = doc.modelspace()
            
            # Calculate grid box boundaries (use the provided coordinates directly)
            box_left = frame_left
            box_top = frame_top
            box_right = frame_right
            box_bottom = frame_bottom
            
            box_width = box_right - box_left
            box_height = box_bottom - box_top
            
            # Add 3 circles arranged in pyramid pattern (diameter = 10 pixels, radius = 5)
            circle_radius = 5.0  # 10 pixel diameter = 5 pixel radius
            
            # Calculate positions for pyramid arrangement
            # Top third: 1 circle centered horizontally
            top_circle_x = box_left + (box_width / 2)
            top_circle_y = box_top + (box_height / 3)
            
            # Bottom third: 2 circles, spaced apart horizontally  
            bottom_y = box_top + (2 * box_height / 3)
            bottom_left_x = box_left + (box_width / 3)
            bottom_right_x = box_left + (2 * box_width / 3)
            
            # Add circles on CIRCLES layer
            msp.add_circle((float(top_circle_x), float(top_circle_y)), circle_radius).dxf.layer = "CIRCLES"
            msp.add_circle((float(bottom_left_x), float(bottom_y)), circle_radius).dxf.layer = "CIRCLES"
            msp.add_circle((float(bottom_right_x), float(bottom_y)), circle_radius).dxf.layer = "CIRCLES"
            
            # Add each contour
            for i, contour in enumerate(contours):
                points = []
                for point in contour:
                    x, y = point
                    points.append((float(x), float(y)))
                
                # Close the contour by adding the first point at the end
                if len(points) > 2:
                    points.append(points[0])
                    
                    # Create contour polyline
                    contour_polyline = msp.add_lwpolyline(points)
                    contour_polyline.closed = True
                    contour_polyline.dxf.layer = f"CONTOUR_{i+1}"
            
            # Save DXF file
            doc.saveas(dxf_path)
            
        except Exception as e:
            raise Exception(f"Error creating DXF file: {e}")

    def detect_blob(self, image, target_color, tolerance=30):
        """Simple blob detection for any box."""
        try:
            # Convert QColor to BGR format for OpenCV
            target_bgr = np.array([target_color.blue(), target_color.green(), target_color.red()], dtype=np.uint8)
            
            # Create color range for matching
            lower_bound = np.clip(target_bgr.astype(np.int32) - tolerance, 0, 255).astype(np.uint8)
            upper_bound = np.clip(target_bgr.astype(np.int32) + tolerance, 0, 255).astype(np.uint8)
            
            print(f"  Searching for BGR({target_bgr[0]}, {target_bgr[1]}, {target_bgr[2]}) with tolerance {tolerance}")
            
            # Create mask for the target color range
            mask = cv2.inRange(image, lower_bound, upper_bound)
            
            # Count pixels
            matching_pixels = cv2.countNonZero(mask)
            print(f"  Found {matching_pixels} matching pixels")
            
            if matching_pixels == 0:
                return []
            
            # Find contours
            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            print(f"  Found {len(contours)} raw contours")
            
            if not contours:
                return []
            
            # Filter by area
            min_area = 50
            filtered_contours = []
            for cnt in contours:
                area = cv2.contourArea(cnt)
                if area > min_area:
                    filtered_contours.append(cnt)
                    print(f"  Contour accepted: area={area}")
            
            return filtered_contours
            
        except Exception as e:
            print(f"Error in detect_a1_blob: {e}")
            return []

    def on_overlap_check_clicked(self):
        """Handle Overlap Check button click - highlight all polygon overlaps"""
        if not self.canvas_container.canvas.polygons:
            QMessageBox.information(self, "Info", "No tiles loaded to check overlaps.")
            return
        
        # Toggle overlap check mode
        if hasattr(self.canvas_container.canvas, 'overlap_check_mode') and self.canvas_container.canvas.overlap_check_mode:
            # Turn off overlap check mode
            self.canvas_container.canvas.overlap_check_mode = False
            self.overlap_btn.setText("Overlap Check")
            self.overlap_btn.setStyleSheet("")
            self.canvas_container.canvas.overlap_highlights = []
        else:
            # Turn on overlap check mode
            self.overlap_btn.setText("Processing...")
            self.overlap_btn.setEnabled(False)
            QApplication.processEvents()
            
            # Find overlapping polygons
            overlap_pairs = self.find_overlapping_polygons()
            
            # Store highlights and enable overlap check mode
            self.canvas_container.canvas.overlap_highlights = overlap_pairs
            self.canvas_container.canvas.overlap_check_mode = True
            
            # Update button appearance
            self.overlap_btn.setText("Hide Overlaps")
            self.overlap_btn.setStyleSheet("background-color: #ffcccc;")  # Light red background
            self.overlap_btn.setEnabled(True)
            
            # Show results
            total_polygons_affected = len(set([idx for pair in overlap_pairs for idx in pair]))
            QMessageBox.information(
                self, 
                "Overlap Check Results", 
                f"Found {len(overlap_pairs)} overlap pairs.\n"
                f"{total_polygons_affected} polygons are involved in overlaps.\n"
                f"Overlapping polygons are highlighted with thick red outlines."
            )
        
        # Refresh the display
        self.canvas_container.canvas.invalidate_cache()
        self.canvas_container.canvas.update()

    def find_overlapping_polygons(self):
        """
        Find all pairs of overlapping polygons using an efficient spatial index (R-tree).
        This check includes the thickness of the polygon frames (edge_width).
        """
        from shapely.strtree import STRtree
        import time

        start_time = time.time()
        overlap_pairs = []
        polygons = self.canvas_container.canvas.polygons
        edge_width = self.canvas_container.canvas.edge_width
        
        if not polygons:
            return []

        # The buffer amount is half the edge width, to account for the stroke
        buffer_amount = edge_width / 2.0
        print(f"Starting overlap check for {len(polygons)} polygons using STRtree with edge_width {edge_width} (buffer: {buffer_amount})...")

        # Create a list of buffered polygons for the check
        # We only buffer valid polygons
        original_indices = [i for i, p in enumerate(polygons) if p.is_valid]
        buffered_polygons = [polygons[i].buffer(buffer_amount) for i in original_indices]

        if not buffered_polygons:
            print("No valid polygons to check.")
            return []

        # Create a spatial index (R-tree) for the buffered polygons
        try:
            tree = STRtree(buffered_polygons)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to create spatial index. Is 'rtree' installed?\nError: {e}")
            return []

        processed_pairs = set()
        actual_overlap_checks = 0

        for i_buffered, poly1_buffered in enumerate(buffered_polygons):
            
            if i_buffered % 100 == 0 and i_buffered > 0:
                print(f"Processing polygon {i_buffered}/{len(buffered_polygons)}")

            # Query the tree for polygons that potentially intersect with the buffered polygon's bounding box
            possible_matches_indices = tree.query(poly1_buffered)

            for j_buffered in possible_matches_indices:
                # Don't compare a polygon with itself
                if i_buffered == j_buffered:
                    continue

                # Get original indices from our map
                i_original = original_indices[i_buffered]
                j_original = original_indices[j_buffered]

                # Avoid duplicate checks (e.g., (1, 2) and (2, 1))
                pair = tuple(sorted((i_original, j_original)))
                if pair in processed_pairs:
                    continue
                
                processed_pairs.add(pair)
                actual_overlap_checks += 1

                poly2_buffered = buffered_polygons[j_buffered]

                try:
                    # Perform the more expensive intersection check on the buffered polygons
                    if poly1_buffered.intersects(poly2_buffered):
                        # Make sure they actually share area (not just touch at a boundary)
                        intersection = poly1_buffered.intersection(poly2_buffered)
                        if hasattr(intersection, 'area') and intersection.area > 0.01:
                            overlap_pairs.append((i_original, j_original))
                except Exception:
                    # Skip problematic polygon pairs
                    continue
        
        end_time = time.time()
        print(f"Overlap check completed in {end_time - start_time:.2f} seconds")
        print(f"Total comparisons (after spatial index): {actual_overlap_checks}")
        print(f"Found {len(overlap_pairs)} overlapping pairs")
        
        return overlap_pairs

    def bounding_boxes_overlap(self, bounds1, bounds2):
        """Check if two bounding boxes overlap"""
        # bounds format: (minx, miny, maxx, maxy)
        return not (bounds1[2] < bounds2[0] or bounds2[2] < bounds1[0] or
                   bounds1[3] < bounds2[1] or bounds2[3] < bounds1[1])

    def save_visible_array(self):
        """Save visible polygons to CSV file in the same format as uploaded"""
        if not self.canvas_container.canvas.polygons:
            QMessageBox.warning(self, "Warning", "No polygons loaded to save.")
            return
        
        # Get visible polygons that meet minimum area requirement
        visible_polygons, visible_colors = self.canvas_container.canvas.get_visible_polygons_with_colors()
        
        if not visible_polygons:
            QMessageBox.warning(self, "Warning", "No visible polygons meet the minimum area requirement.")
            return
        
        # Open file dialog to choose save location
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Save Visible Array as CSV",
            "",
            "CSV Files (*.csv);;All Files (*)"
        )
        
        if not filename:
            return  # User cancelled
        
        try:
            with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
                import csv
                import json
                writer = csv.writer(csvfile)
                
                # Write header with alpha channel support
                writer.writerow(['polygon_id', 'coordinates', 'color_r', 'color_g', 'color_b', 'color_a'])
                
                # Write each visible polygon
                for i, (polygon, color) in enumerate(zip(visible_polygons, visible_colors)):
                    # Extract coordinates as a list of [x, y] pairs
                    coords = list(polygon.exterior.coords)
                    # Convert to JSON string for storage (same format as loaded)
                    coords_json = json.dumps([[float(x), float(y)] for x, y in coords])
                    
                    # Extract RGBA values (convert from QColor to 0-1 range)
                    r = color.red() / 255.0
                    g = color.green() / 255.0  
                    b = color.blue() / 255.0
                    a = color.alpha() / 255.0  # Add alpha channel
                    
                    # Write row with alpha
                    writer.writerow([i, coords_json, r, g, b, a])
            
            QMessageBox.information(
                self, 
                "Success", 
                f"Saved {len(visible_polygons)} visible polygons to {filename}"
            )
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save file: {str(e)}")


if __name__ == "__main__":
    import sys
    from PyQt5.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    window = MosaicEditor()
    window.show()
    sys.exit(app.exec_())
