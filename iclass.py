import os
import base64
import requests
import cv2
import numpy as np
import pytesseract
from dotenv import load_dotenv
import re
import json

load_dotenv()    

def detect_table_cells(image_path, debug=False):
    # Read the image
    image = cv2.imread(image_path)
    if image is None:
        raise Exception(f"Could not read image at {image_path}")
    
    debug_image = image.copy()
    
    # Convert to grayscale
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    # Enhance image contrast
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
    gray = clahe.apply(gray)
    
    # Apply Gaussian blur to reduce noise
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    
    # Apply Canny edge detection
    edges = cv2.Canny(blurred, 50, 150)
    
    # Dilate the edges to connect nearby edges
    kernel = np.ones((3, 3), np.uint8)
    dilated_edges = cv2.dilate(edges, kernel, iterations=2)
    
    if debug:
        cv2.imwrite(image_path.rsplit('.', 1)[0] + '_edges.jpg', dilated_edges)
    
    # Find contours in the edge image
    contours, _ = cv2.findContours(dilated_edges, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    
    # Filter contours by area and shape
    min_area = image.shape[0] * image.shape[1] * 0.0004
    max_area = image.shape[0] * image.shape[1] * 0.11    # Increased maximum area threshold
    
    # Find colored regions (potential class cells)
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    
    # Use a more flexible approach to detect colored regions
    # Instead of predefined color ranges, detect any non-white/non-gray regions
    # Extract saturation channel (S in HSV)
    s_channel = hsv[:,:,1]
    # Extract value channel (V in HSV)
    v_channel = hsv[:,:,2]
    
    # Create a mask for colored regions (regions with sufficient saturation)
    color_mask = np.zeros_like(gray)
    color_mask[(s_channel > 20) & (v_channel > 20)] = 255
    
    # Dilate the color mask to connect nearby regions
    color_mask = cv2.dilate(color_mask, kernel, iterations=3)
    
    if debug:
        cv2.imwrite(image_path.rsplit('.', 1)[0] + '_color_mask.jpg', color_mask)
    
    # Find contours in the color mask
    color_contours, _ = cv2.findContours(color_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    # Combine edge-based contours and color-based contours
    all_contours = contours + color_contours
    
    # Filter and process contours
    cell_contours = []
    for cnt in all_contours:
        x, y, w, h = cv2.boundingRect(cnt)
        area = w * h
        aspect_ratio = float(w) / h if h > 0 else 0
        
        # Filter by area and aspect ratio
        if min_area < area < max_area and 0.1 < aspect_ratio < 7.0:  # Expanded from 0.15-6.0 to 0.1-7.0
            # Check if this contour is not already in the list (avoid duplicates)
            is_duplicate = False
            for existing_cnt in cell_contours:
                ex, ey, ew, eh = cv2.boundingRect(existing_cnt)
                # If there's significant overlap, consider it a duplicate
                overlap_x = max(0, min(x + w, ex + ew) - max(x, ex))
                overlap_y = max(0, min(y + h, ey + eh) - max(y, ey))
                overlap_area = overlap_x * overlap_y
                if overlap_area > 0.7 * min(area, ew * eh):
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                cell_contours.append(cnt)
    
    print(f"Detected {len(cell_contours)} potential cells")
    
    # Sort contours by position (top to bottom, left to right)
    def sort_contours(cnts):
        if not cnts:
            return []
            
        # Sort by Y first (top to bottom)
        sorted_by_y = sorted(cnts, key=lambda c: cv2.boundingRect(c)[1])
        
        # Group contours with similar Y values
        y_groups = []
        current_group = [sorted_by_y[0]]
        current_y = cv2.boundingRect(sorted_by_y[0])[1]
        
        for cnt in sorted_by_y[1:]:
            y = cv2.boundingRect(cnt)[1]
            if abs(y - current_y) < 30:  # Cells in same row should have similar y values
                current_group.append(cnt)
            else:
                y_groups.append(current_group)
                current_group = [cnt]
                current_y = y
        
        if current_group:
            y_groups.append(current_group)
        
        # Sort each group by X (left to right)
        result = []
        for group in y_groups:
            sorted_group = sorted(group, key=lambda c: cv2.boundingRect(c)[0])
            result.extend(sorted_group)
        
        return result
    
    cell_contours = sort_contours(cell_contours)
    
    # Function to determine day of week based on x-position
    def determine_day_of_week(x_position, image_width):
        """
        Determine the day of the week (Monday to Sunday) based on x-position in the image.
        
        Args:
            x_position: The x-coordinate of the cell
            image_width: The width of the entire image
            
        Returns:
            A tuple containing (day_index, day_name) where day_index is 0-6 (Monday-Sunday)
            and day_name is the Chinese name of the day
        """
        # Calculate relative position (0 to 1) across the image width
        relative_pos = x_position / image_width
        
        # Divide the image width into 7 equal segments for the 7 days of the week
        # We use 7 segments because the table has Monday to Sunday (7 days)
        day_index = min(int(relative_pos * 7), 6)  # Ensure index is at most 6
        
        # Chinese names for days of the week
        day_names = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
        
        return day_index, day_names[day_index]
    
    # Extract cell information
    cells = []
    image_width = image.shape[1]  # Get the width of the image
    
    for i, cnt in enumerate(cell_contours):
        x, y, w, h = cv2.boundingRect(cnt)
        
        # Extract cell ROI
        cell_roi = gray[y:y+h, x:x+w]
        
        # Skip if cell is too small
        if w < 15 or h < 15:
            continue
        
        # Enhance cell image for OCR
        # Apply OCR to cell
        custom_config = r'--oem 3 --psm 6'
        text = pytesseract.image_to_string(cell_roi, lang='chi_sim+eng', config=custom_config)
        
        # Get cell color (average color in the cell region)
        cell_color = np.mean(image[y:y+h, x:x+w], axis=(0, 1)).astype(int)
        
        # Determine day of week based on x-position
        day_index, day_name = determine_day_of_week(x, image_width)
        
        cells.append({
            'id': i,
            'text': text.strip(),
            'position': (x, y, w, h),
            'color': cell_color.tolist(),
            'is_header': False,
            'is_active': False,
            'area': w * h,  # Store the area for size grouping
            'day_index': day_index,  # 0-6 for Monday-Sunday
            'day_name': day_name     # Chinese name of the day
        })
    
    # Group cells by size
    def group_cells_by_size(cells, tolerance=0.01):  # Increased from 0.4 to 0.5 to be more inclusive
        """Group cells by their height and width with a tolerance percentage."""
        if not cells:
            return []
        
        # Calculate size groups
        size_groups = {}
        for cell in cells:
            # Extract width and height from position
            _, _, width, height = cell['position']
            
            # Find if this cell fits in an existing group
            found_group = False
            for group_key in list(size_groups.keys()):
                group_width, group_height = group_key
                
                # Check if width and height are within tolerance of group dimensions
                width_diff = abs(width - group_width) / max(width, group_width)
                height_diff = abs(height - group_height) / max(height, group_height)
                
                # Both dimensions must be within tolerance
                if width_diff < tolerance and height_diff < tolerance:
                    size_groups[group_key].append(cell)
                    found_group = True
                    break
            
            # If no suitable group found, create a new one
            if not found_group:
                size_groups[(width, height)] = [cell]
        
        # Find the largest group
        if size_groups:
            largest_group = max(size_groups.values(), key=len)
            return largest_group
        return []
    
    # Analyze cell size statistics
    def analyze_cell_sizes(cells):
        """Analyze the distribution of cell sizes."""
        if not cells:
            return {}
        
        areas = [cell['area'] for cell in cells]
        widths = [cell['position'][2] for cell in cells]
        heights = [cell['position'][3] for cell in cells]
        
        stats = {
            'area': {
                'min': min(areas),
                'max': max(areas),
                'mean': sum(areas) / len(areas),
                'median': sorted(areas)[len(areas) // 2]
            },
            'width': {
                'min': min(widths),
                'max': max(widths),
                'mean': sum(widths) / len(widths),
                'median': sorted(widths)[len(widths) // 2]
            },
            'height': {
                'min': min(heights),
                'max': max(heights),
                'mean': sum(heights) / len(heights),
                'median': sorted(heights)[len(heights) // 2]
            }
        }
        return stats
    
    # Filter cells to keep only those with the most common size
    original_cells = cells.copy()
    filtered_cells = group_cells_by_size(cells, tolerance=0.1)
    if filtered_cells:
        print(f"Filtered to {len(filtered_cells)} cells with similar size out of {len(cells)} total cells")
        cells = filtered_cells
        
   
    # Identify header cells and active cells
    if cells:
        active_cells = []
        for cell in cells:
            if not cell['is_header']:
                text = cell['text']
                
                # Check if cell contains class information
                if text and not text.isspace():
                    # Check for patterns that indicate a class
                    has_time_pattern = bool(re.search(r'\d{1,2}[:：]\d{2}', text))
                    has_location_pattern = bool(re.search(r'[A-Za-z0-9]+\s*[A-Za-z0-9]*', text))
                    
                    # Consider cells with meaningful content as active
                    if len(text.strip()) > 0 or has_time_pattern or has_location_pattern:
                        cell['is_active'] = True
                        active_cells.append(cell)
                
                # Also consider colored cells as active even if they don't have text
                # (some class cells might have poor OCR results but are visibly colored)
                elif not np.all(np.array(cell['color']) > 230):  # Increased from 210 to 230 to include more cells
                    cell['is_active'] = True
                    active_cells.append(cell)
    
    if debug:
        # Create a copy of the original image for showing all detected cells
        all_cells_debug = image.copy()
        
        # Draw all initially detected cells in light gray
        for cell in cells:
            x, y, w, h = cell['position']
            cv2.rectangle(all_cells_debug, (x, y), (x+w, y+h), (200, 200, 200), 1)
        
        # Save debug image showing all cells
        all_cells_debug_path = image_path.rsplit('.', 1)[0] + '_all_cells.jpg'
        cv2.imwrite(all_cells_debug_path, all_cells_debug)
        
        # Draw all detected cells
        for cell in cells:
            x, y, w, h = cell['position']
            
            # Draw cell borders in light gray
            cv2.rectangle(debug_image, (x, y), (x+w, y+h), (200, 200, 200), 1)
            
            # Mark header cells in blue
            if cell['is_header']:
                cv2.rectangle(debug_image, (x, y), (x+w, y+h), (255, 0, 0), 2)
            
            # Mark active cells in green
            if cell['is_active']:
                cv2.rectangle(debug_image, (x, y), (x+w, y+h), (0, 255, 0), 2)
                # Add cell number and day of week
                cv2.putText(debug_image, f"{list(filter(lambda c: c['is_active'], cells)).index(cell) + 1} ({cell['day_name']})", 
                          (x, y-5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
        
        # Save debug image
        debug_path = image_path.rsplit('.', 1)[0] + '_debug.jpg'
        cv2.imwrite(debug_path, debug_image)
        print(f"Total cells detected: {len(cells)}")
        print(f"Header cells: {sum(1 for cell in cells if cell['is_header'])}")
        print(f"Active cells: {sum(1 for cell in cells if cell['is_active'])}")
        
    
    # Return only active cells
    return [cell for cell in cells if cell['is_active']]

def extract_column_images(image_path, cells, debug=False):
    """
    Extract column images for each day of the week from the cells.
    
    Args:
        image_path: Path to the original image
        cells: List of detected cells
        debug: Whether to save debug images
        
    Returns:
        A dictionary mapping day_index to column image paths
    """
    # Read the original image
    image = cv2.imread(image_path)
    if image is None:
        raise Exception(f"Could not read image at {image_path}")
    
    # Group cells by day_index
    day_columns = {}
    for i in range(7):  # 0-6 for Monday-Sunday
        day_columns[i] = [cell for cell in cells if cell['day_index'] == i]
    
    # Create column images
    column_image_paths = {}
    day_names = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
    
    # Get the overall top position to include headers
    # We'll use this to ensure all columns include the header area
    overall_top = 0
    if image.shape[0] > 100:  # If image is tall enough
        # Use a percentage of the image height as the header area
        # This ensures we capture the header even if no cells are detected in it
        overall_top = int(image.shape[0] * 0.05)  # Use top 5% of image
    
    for day_index, day_cells in day_columns.items():
        if not day_cells:
            continue
        
        # Find the bounding box that contains all cells for this day
        min_x = min(cell['position'][0] for cell in day_cells) if day_cells else 0
        min_y = min(cell['position'][1] for cell in day_cells) if day_cells else 0
        max_x = max(cell['position'][0] + cell['position'][2] for cell in day_cells) if day_cells else 0
        max_y = max(cell['position'][1] + cell['position'][3] for cell in day_cells) if day_cells else 0
        
        # Add some padding
        padding = 10
        min_x = max(0, min_x - padding)
        
        # Extend the top to include the header area
        min_y = max(0, min(min_y, overall_top) - padding)
        
        max_x = min(image.shape[1], max_x + padding)
        max_y = min(image.shape[0], max_y + padding)
        
        # Extract the column image
        column_image = image[min_y:max_y, min_x:max_x].copy()
        
        # Save the column image
        column_path = image_path.rsplit('.', 1)[0] + f'_column_{day_index}_{day_names[day_index]}.jpg'
        cv2.imwrite(column_path, column_image)
        
        # Add to the dictionary
        column_image_paths[day_index] = column_path
        
        if debug:
            # Create a debug image showing the cells in this column
            debug_column = column_image.copy()
            for cell in day_cells:
                # Adjust coordinates to be relative to the column image
                x, y, w, h = cell['position']
                x_rel = x - min_x
                y_rel = y - min_y
                
                # Draw cell borders
                cv2.rectangle(debug_column, (x_rel, y_rel), (x_rel+w, y_rel+h), (0, 255, 0), 2)
                
                # Add cell text
                cv2.putText(debug_column, cell['text'][:10], 
                          (x_rel, y_rel-5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
            
            # Save debug column image
            debug_column_path = image_path.rsplit('.', 1)[0] + f'_column_{day_index}_{day_names[day_index]}_debug.jpg'
            cv2.imwrite(debug_column_path, debug_column)
    
    return column_image_paths

def analyze_image(image_path, prompt="What's in this image?", debug=False):
    try:
        # First detect and extract text from table cells
        cell_contents = detect_table_cells(image_path, debug=debug)
        
        # Extract column images for each day
        column_image_paths = extract_column_images(image_path, cell_contents, debug=debug)
        print(column_image_paths)
        
        # Prepare data for all columns
        day_names = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
        
        # Create a structured text description for all columns
        all_columns_description = "Schedule by day of week:\n\n"
        
        # Create a more specific prompt that instructs the model to return data in the expected format
        # Using the prompt format from app.py
        enhanced_prompt = f"""

This is a class schedule table. For each day and each class cell, extract the following information:
- Class name
- Class date (including day of week)
- Class time (start-end)
- Class location
- Class instructor
- Any other relevant details

Return your analysis as a JSON array of class objects with the following structure:
[
  {{
    "class_name": "Class Name",
    "class_date": "02.15 周六",
    "class_time": "10:00-11:00",
    "class_location": "Class Location",
    "class_instructor": "Class Instructor",
    "class_score_stars": 0
  }},
  ...more classes...
]

Make sure to include all classes from all days of the week in a single flat array.
"""
        
        # Prepare all image data for a single API call
        content_items = [{"type": "text", "text": enhanced_prompt + "\n\n" + all_columns_description}]
        
        # Add each column's information and image
        for day_index, column_path in column_image_paths.items():
            # Add column image
            with open(column_path, "rb") as image_file:
                base64_image = base64.b64encode(image_file.read()).decode("utf-8")
                content_items.append({
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}
                })
        
        # Make a single API call with all content
        api_key = os.environ.get("OPENAI_API_KEY")
        headers = {
            "Authorization": f"Bearer {api_key}",
            "X-Title": "iClass App"
        }
        
        # Create message payload with all content items
        payload = {
            "model": "google/gemini-2.0-flash-lite-001",
            "messages": [
                {
                    "role": "user",
                    "content": content_items
                }
            ],
            "response_format": {"type": "json_object"}
        }
        
        # Make request to OpenRouter API
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=payload
        )
        
        if response.status_code != 200:
            raise Exception(f"API request failed with status {response.status_code}: {response.text}")
        
        # Process the response
        api_response = response.json()["choices"][0]["message"]["content"]
        
        # Parse the JSON response
        try:
            parsed_response = json.loads(api_response)
            
            # If the response is not already a list, try to extract the list
            # This handles cases where the API might wrap the list in another object
            if not isinstance(parsed_response, list):
                # Check if there's a key that contains a list
                for key, value in parsed_response.items():
                    if isinstance(value, list) and len(value) > 0:
                        parsed_response = value
                        break
                
                # If we still don't have a list, try to extract from nested structure
                if not isinstance(parsed_response, list) and "days" in parsed_response:
                    # Flatten the days structure into a single list of classes
                    classes = []
                    for day, day_data in parsed_response["days"].items():
                        if isinstance(day_data, list):
                            # If day_data is already a list, extend classes with it
                            classes.extend(day_data)
                        elif isinstance(day_data, dict) and "classes" in day_data:
                            # If day_data has a classes key with a list, extend classes with it
                            classes.extend(day_data["classes"])
                        elif isinstance(day_data, dict):
                            # If day_data is a dict with class info, add it as a single class
                            # First add the day information if not already present
                            class_info = day_data.copy()
                            if "class_date" not in class_info:
                                class_info["class_date"] = day
                            classes.append(class_info)
                    
                    if classes:
                        parsed_response = classes
            
            # Ensure each class has the required fields
            for class_item in parsed_response if isinstance(parsed_response, list) else []:
                if "class_name" not in class_item:
                    class_item["class_name"] = None
                if "class_date" not in class_item:
                    class_item["class_date"] = None
                if "class_time" not in class_item:
                    class_item["class_time"] = None
                if "class_location" not in class_item:
                    class_item["class_location"] = None
                if "class_instructor" not in class_item:
                    class_item["class_instructor"] = None
                if "class_score_stars" not in class_item:
                    class_item["class_score_stars"] = 0
            
            return parsed_response
        except json.JSONDecodeError:
            # If JSON parsing fails, return the raw response
            return api_response
    finally:
        # Clean up all generated images
        if not debug:  # Only clean up if not in debug mode
            try:
                # Clean up the original uploaded image
                if os.path.exists(image_path):
                    os.remove(image_path)
                    print(f"Removed original image: {image_path}")
                
                # Clean up all generated column images
                base_path = image_path.rsplit('.', 1)[0]
                for file in os.listdir(os.path.dirname(image_path)):
                    if file.startswith(os.path.basename(base_path)) and file != os.path.basename(image_path):
                        file_path = os.path.join(os.path.dirname(image_path), file)
                        os.remove(file_path)
                        print(f"Removed processed image: {file_path}")
            except Exception as e:
                print(f"Error during cleanup: {str(e)}")

# Test function
def test_column_extraction(image_path):
    print(f"Testing column extraction on {image_path}")
    cell_contents = detect_table_cells(image_path, debug=True)
    column_image_paths = extract_column_images(image_path, cell_contents, debug=True)
    
    print(f"Extracted {len(column_image_paths)} column images:")
    day_names = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
    for day_index, path in column_image_paths.items():
        print(f"  Day {day_index+1} ({day_names[day_index]}): {path}")
    
    return column_image_paths

# Original test function
def test_cell_detection(image_path):
    print(f"Testing cell detection on {image_path}")
    cell_contents = detect_table_cells(image_path, debug=True)
    
    # Print detailed information about each cell
    for i, cell in enumerate(cell_contents):
        print(f"Cell {i+1}:")
        print(f"  Position: {cell['position']}")
        print(f"  Day: {cell['day_name']} (index: {cell['day_index']})")
        print(f"  Text: {cell['text']}")
        print(f"  Color: {cell['color']}")
        print("---")
    
    return len(cell_contents)
