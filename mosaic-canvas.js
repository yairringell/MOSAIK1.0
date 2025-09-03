// Debug logging function
function debugLog(message) {
    var debugElement = document.getElementById('debugLog');
    var timestamp = new Date().toLocaleTimeString();
    debugElement.textContent += '[' + timestamp + '] ' + message + '\n';
    debugElement.scrollTop = debugElement.scrollHeight;
}

function clearDebug() {
    document.getElementById('debugLog').textContent = 'Debug log cleared...\n';
}

// Regular JavaScript for UI interactions
function loadCSV(event) {
    debugLog('Starting CSV load process...');
    
    var file = event.target.files[0];
    if (!file) {
        debugLog('ERROR: No file selected');
        return;
    }

    debugLog('File selected: ' + file.name + ' (size: ' + file.size + ' bytes)');

    var reader = new FileReader();
    reader.onload = function(e) {
        debugLog('File read successfully, parsing CSV...');
        var csv = e.target.result;
        debugLog('CSV content length: ' + csv.length + ' characters');
        debugLog('First 200 chars: ' + csv.substring(0, 200) + '...');
        
        // Trigger the PaperScript parseCSV function
        try {
            window.paperFunctions.clearPolygons();
            debugLog('Paper.js polygons cleared');
            
            var lines = csv.trim().split('\n');
            debugLog('Split into ' + lines.length + ' lines');
            
            if (lines.length < 2) {
                debugLog('ERROR: Not enough lines in CSV (need header + data)');
                return;
            }

            var header = lines[0].split(',');
            debugLog('Header: ' + header.join(' | '));

            // Find column indices
            var coordsIndex = -1, colorRIndex = -1, colorGIndex = -1, colorBIndex = -1;
            
            for (var i = 0; i < header.length; i++) {
                var h = header[i].toLowerCase();
                if (h.includes('coordinates') || h.includes('polygon_coords')) coordsIndex = i;
                if (h.includes('color_r')) colorRIndex = i;
                if (h.includes('color_g')) colorGIndex = i;
                if (h.includes('color_b')) colorBIndex = i;
            }

            debugLog('Column indices - coords:' + coordsIndex + ', R:' + colorRIndex + ', G:' + colorGIndex + ', B:' + colorBIndex);

            if (coordsIndex === -1) {
                debugLog('ERROR: Could not find coordinates column');
                return;
            }

            var allCoords = [];
            var polygonCount = 0;
            var errorCount = 0;

            for (var i = 1; i < lines.length && i < 6; i++) { // Process first 5 rows for debugging
                debugLog('Processing row ' + i + ': ' + lines[i]);
                
                var row = parseCSVRowJS(lines[i]);
                debugLog('Parsed into ' + row.length + ' columns: [' + row.join('] [') + ']');
                
                if (row.length < header.length) {
                    debugLog('WARNING: Row ' + i + ' has fewer columns than header');
                    continue;
                }

                try {
                    // Parse coordinates
                    var coordsStr = row[coordsIndex] || '';
                    debugLog('Raw coordinates: ' + coordsStr);
                    
                    coordsStr = coordsStr.replace(/"/g, '').trim();
                    debugLog('Cleaned coordinates: ' + coordsStr);
                    
                    // Convert Python tuple format to JSON format
                    // Replace parentheses with square brackets for JSON parsing
                    var jsonCoordsStr = coordsStr.replace(/\(/g, '[').replace(/\)/g, ']');
                    debugLog('JSON format: ' + jsonCoordsStr);
                    
                    // Parse JSON coordinate array
                    var coords = JSON.parse(jsonCoordsStr);
                    debugLog('Parsed ' + coords.length + ' coordinate pairs');
                    
                    if (coords.length < 3) {
                        debugLog('WARNING: Polygon has less than 3 points, skipping');
                        continue;
                    }

                    // Parse colors
                    var r = parseFloat(row[colorRIndex] || 0);
                    var g = parseFloat(row[colorGIndex] || 0);
                    var b = parseFloat(row[colorBIndex] || 0);
                    debugLog('Raw colors: R=' + r + ', G=' + g + ', B=' + b);

                    // Convert 0-1 range to 0-255 if needed
                    if (r <= 1 && g <= 1 && b <= 1) {
                        r = Math.floor(r * 255);
                        g = Math.floor(g * 255);
                        b = Math.floor(b * 255);
                        debugLog('Converted colors to: R=' + r + ', G=' + g + ', B=' + b);
                    }

                    // If all colors are 0 (black/transparent), use white for visibility
                    if (r === 0 && g === 0 && b === 0) {
                        r = 255;
                        g = 255;
                        b = 255;
                        debugLog('Converted transparent polygon to white: R=' + r + ', G=' + g + ', B=' + b);
                    }

                    // Create Paper.js path using the exposed function
                    var success = window.paperFunctions.createPolygon(coords, r, g, b);
                    if (success) {
                        debugLog('Successfully created polygon ' + polygonCount);
                        polygonCount++;
                    } else {
                        debugLog('ERROR: Failed to create polygon');
                        errorCount++;
                    }
                    
                } catch (error) {
                    errorCount++;
                    debugLog('ERROR parsing row ' + i + ': ' + error.message);
                }
            }

            // Process remaining rows without detailed logging
            debugLog('Processing remaining ' + (lines.length - 6) + ' rows...');
            for (var i = 6; i < lines.length; i++) {
                var row = parseCSVRowJS(lines[i]);
                if (row.length < header.length || coordsIndex === -1) continue;

                try {
                    var coordsStr = row[coordsIndex] || '';
                    coordsStr = coordsStr.replace(/"/g, '').trim();
                    
                    // Convert Python tuple format to JSON format
                    var jsonCoordsStr = coordsStr.replace(/\(/g, '[').replace(/\)/g, ']');
                    var coords = JSON.parse(jsonCoordsStr);
                    if (coords.length < 3) continue;

                    var r = parseFloat(row[colorRIndex] || 0);
                    var g = parseFloat(row[colorGIndex] || 0);
                    var b = parseFloat(row[colorBIndex] || 0);

                    if (r <= 1 && g <= 1 && b <= 1) {
                        r = Math.floor(r * 255);
                        g = Math.floor(g * 255);
                        b = Math.floor(b * 255);
                    }

                    if (r === 0 && g === 0 && b === 0) {
                        r = 255;
                        g = 255;
                        b = 255;
                    }

                    var success = window.paperFunctions.createPolygon(coords, r, g, b);
                    if (success) {
                        polygonCount++;
                    } else {
                        errorCount++;
                    }
                    
                } catch (error) {
                    errorCount++;
                }
            }

            debugLog('Finished processing. Total polygons: ' + polygonCount + ', Errors: ' + errorCount);

            // No auto-fitting - polygons displayed at original size with top-left as (0,0)
            debugLog('Polygons displayed at original size, no auto-fitting applied');

            document.getElementById('fileInfo').textContent = 'Loaded: ' + file.name + ' (' + polygonCount + ' polygons)';
            debugLog('SUCCESS: File loaded completely');
            
        } catch (error) {
            debugLog('FATAL ERROR: ' + error.message);
            debugLog('Stack trace: ' + error.stack);
        }
    };
    
    reader.onerror = function() {
        debugLog('ERROR: Failed to read file');
    };
    
    reader.readAsText(file);
}

function parseCSVRowJS(row) {
    var result = [];
    var current = '';
    var inQuotes = false;
    
    for (var i = 0; i < row.length; i++) {
        var char = row[i];
        if (char === '"') {
            inQuotes = !inQuotes;
        } else if (char === ',' && !inQuotes) {
            result.push(current);
            current = '';
        } else {
            current += char;
        }
    }
    result.push(current);
    return result;
}
