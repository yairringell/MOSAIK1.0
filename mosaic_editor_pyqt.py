#!/usr/bin/env python3
"""
Mosaic Editor - Pure PyQt5 Implementation
A professional mosaic viewing and editing application using only PyQt5 for rendering.
"""

import sys
import csv
import json
import numpy as np
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
    
    def __init__(self):
        super().__init__()
        self.colors = []
        self.selected_color = QColor(0, 0, 0)  # Default to black
        self.color_size = 20  # Size of each color square (20x20 pixels)
        self.selected_color_width = 40  # Width of selected color rectangle
        self.selected_color_height = 20  # Height of selected color rectangle
        self.setFixedHeight(60)  # Fixed height for the palette (adjusted for larger squares)
        self.setMinimumWidth(450)  # Increased slightly to accommodate selection rectangle next to palette
        self.load_palette_colors()
        
    def load_palette_colors(self):
        """Load colors from color_palette2.csv file"""
        import os
        
        # Look for color_palette2.csv in the current directory
        palette_path = os.path.join(os.path.dirname(__file__), 'color_palette2.csv')
        
        if os.path.exists(palette_path):
            try:
                with open(palette_path, 'r', encoding='utf-8') as file:
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
                
            except Exception as e:
                self.load_default_colors()
        else:
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
        self.background_offset_x = -7.0  # X offset for background image
        self.background_offset_y = -10.0  # Y offset for background image
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
        
        # Grid variables
        self.show_grid = False  # Whether to show the grid
        self.grid_size = 67  # Size of each individual grid box/cell in world coordinates
        self.grid_offset_x = 0  # Grid offset in world coordinates
        self.grid_offset_y = 0  # Grid offset in world coordinates
        self.grid_dragging = False  # Whether we're dragging the grid
        self.grid_drag_start = None  # Starting point for grid drag
        self.grid_drag_world_start = None  # Starting world coordinates for grid drag
        
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
        self.drag_start_world_pos = None
        
        # Control point editing
        self.selected_control_point = -1  # Index of selected control point
        self.is_dragging_control_point = False
        self.control_point_size = 8  # Size of control point circles
        
        # Paint mode variables
        self.paint_mode = False
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
        
        # Draw control points for selected polygon
        if self.selected_polygon_index >= 0:
            self.draw_control_points(painter)
    
    def draw_grid(self, painter):
        """Draw the 6x6 grid overlay with draggable handle that scales with zoom"""
        painter.setPen(QPen(QColor(0, 0, 255), 2))  # Blue grid lines
        
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
                # Paint mode - find polygon and paint it
                polygon_index = self.find_polygon_at_point(event.x(), event.y())
                if polygon_index >= 0:
                    self.paint_polygon(polygon_index)
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
        """Handle mouse move for grid dragging, shape dragging, view panning, erasing, or cursor updates"""
        if self.grid_dragging and self.grid_drag_world_start:
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
            if self.grid_dragging:
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
            self.drag_start_world_pos = None
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
                if hasattr(self, 'main_editor') and self.main_editor and hasattr(self.main_editor, 'selected_palette_color') and self.main_editor.selected_palette_color:
                    edge_color = self.main_editor.selected_palette_color
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
        self.bg_offset_x_input.setText('0')
        self.bg_offset_x_input.setPlaceholderText('X offset')
        self.bg_offset_x_input.textChanged.connect(self.on_background_offset_changed)
        offset_layout.addWidget(self.bg_offset_x_input)
        
        offset_layout.addWidget(QLabel('Y:'))
        self.bg_offset_y_input = QLineEdit()
        self.bg_offset_y_input.setText('0')
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
        self.grid_size_input.setText('67')
        self.grid_size_input.setPlaceholderText('Enter box size (e.g., 67)')
        self.grid_size_input.textChanged.connect(self.on_grid_size_changed)
        layout.addWidget(self.grid_size_input)
        
        layout.addWidget(self.create_separator())
        
        layout.addWidget(self.create_separator())
        
        # Statistics
        layout.addWidget(QLabel('Statistics:', font=QFont('Arial', 10, QFont.Bold)))
        
        self.stats_label = QLabel('No file loaded')
        self.stats_label.setWordWrap(True)
        layout.addWidget(self.stats_label)
        
        # Add stretch to push everything up
        layout.addStretch()
    
    def create_separator(self):
        """Create a visual separator line"""
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        return line
    
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
    
    def on_color_selected(self, color):
        """Handle color selection from the palette"""
        # Store the selected color locally and pass it to the canvas
        self.selected_palette_color = color
        # Update the canvas with the selected color for paint mode
        self.canvas_container.canvas.selected_palette_color = color
    
    def keyPressEvent(self, event):
        """Handle global keyboard shortcuts"""
        if event.key() == Qt.Key_P:
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


def main():
    """Main function"""
    app = QApplication(sys.argv)
    app.setApplicationName("Mosaic Editor")
    app.setOrganizationName("Mosaic Tools")
    
    # Set application style
    app.setStyle('Fusion')
    
    # Create and show main window
    window = MosaicEditor()
    window.show()
    
    # Start event loop
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
