"""EaseMyTrip Flight Filter Testing Engine"""

import re
from typing import List, Dict, Any
from dataclasses import dataclass

from playwright.sync_api import sync_playwright, Page

# Import project modules
from src.utils.logger import TestLogger

@dataclass
class TestConfig:
    """Configuration for a single test case"""
    test_id: str
    description: str
    from_city: str
    to_city: str
    departure_date: str
    stops_filter: str
    price_min: int
    price_max: int

class PureUIFilterEngine:
    """Tests EaseMyTrip UI filtering functionality"""
    
    def __init__(self):
        """Initialize UI filter testing engine"""
        test_logger = TestLogger()
        self.logger = test_logger.logger
        
    def test_ui_filter_functionality(self, config: TestConfig) -> Dict[str, Any]:
        """Test EaseMyTrip UI filtering: search → filter → validate results"""
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False)
            page = browser.new_page()
            
            try:
                self.logger.info(f"Testing UI Filter: {config.test_id}")
                self.logger.info(f"   Description: {config.description}")
                self.logger.info(f"   Route: {config.from_city} → {config.to_city}")
                self.logger.info(f"   Date: {config.departure_date}")
                self.logger.info(f"   Filter Test: {config.stops_filter} + ₹{config.price_min:,}-₹{config.price_max:,}")
                
                # 1. Perform flight search
                if not self._perform_flight_search(page, config):
                    return {"status": "FAIL", "reason": "Search failed", "flights": []}
                
                # 2. Get BEFORE filtering count
                before_count = self._count_visible_flights(page)
                self.logger.info(f"   BEFORE filtering: {before_count} flights visible")
                
                # 3. Apply UI filters ONLY
                self._apply_pure_ui_filters(page, config)
                
                # 4. Get AFTER filtering count  
                after_count = self._count_visible_flights(page)
                self.logger.info(f"   AFTER UI filtering: {after_count} flights visible")
                
                # 5. Extract ONLY what the UI shows 
                ui_filtered_flights = self._extract_filtered_flights_only(page, config)
                
                self.logger.info(f"   UI Filter Applied - {len(ui_filtered_flights)} flights data extracted")
                
                # 6. Validate extracted flights meet criteria
                validation_result = self._validate_extracted_flights_meet_criteria(ui_filtered_flights, config)
                
                return {
                    "status": "SUCCESS",
                    "before_count": before_count,
                    "after_count": after_count, 
                    "ui_filtered_flights": ui_filtered_flights,
                    "validation_result": validation_result,
                    "test_config": config.__dict__
                }
                
            except Exception as e:
                self.logger.error(f"   UI Filter Test Error: {e}")
                return {"status": "ERROR", "error": str(e), "flights": []}
                
            finally:
                browser.close()

    def _perform_flight_search(self, page: Page, config: TestConfig) -> bool:
        """Navigate to EaseMyTrip, fill search form, and submit"""
        try:
            # Navigate to EaseMyTrip
            page.goto("https://www.easemytrip.com/", timeout=60000)
            page.wait_for_timeout(3000)
            
            # City Selection 
            self.logger.info(f"     Selecting FROM city: {config.from_city}")
            from_success = self._select_city(page, 'from', config.from_city)
            
            self.logger.info(f"     Selecting TO city: {config.to_city}")  
            to_success = self._select_city(page, 'to', config.to_city)
            
            # Verify selections
            page.wait_for_timeout(1000)
            from_value = page.evaluate("document.querySelector('#FromSector_show').value")
            to_value = page.evaluate("document.querySelector('#Editbox13_show').value")
            self.logger.info(f"     Verified: {from_value} → {to_value}")
            
            if not from_success or not to_success:
                self.logger.error(f"     City selection failed - FROM: {from_success}, TO: {to_success}")
                return False
            
            # Set departure date
            self.logger.info(f"      Setting departure date: {config.departure_date}")
            
            # Remove blocking overlays and prepare date field
            page.evaluate("""
                const overlays = document.querySelectorAll('#overlaybg1, .overlaybg1, .overlay, .overlaybg, #overlaybgg1');
                overlays.forEach(overlay => {
                    if (overlay) {
                        overlay.style.display = 'none';
                        overlay.style.visibility = 'hidden';
                        overlay.style.zIndex = '-1000';
                        try { overlay.remove(); } catch(e) {}
                    }
                });
                
                const dateField = document.querySelector('#ddate');
                if (dateField) {
                    dateField.style.pointerEvents = 'auto';
                    dateField.style.zIndex = '1000';
                    dateField.removeAttribute('readonly');
                }
            """)
            page.wait_for_timeout(1500)
            
            formatted_date = self._format_date_for_input(config.departure_date)
            
            # Click date field and set value
            try:
                page.click('#ddate', timeout=8000)
            except Exception:
                pass  # Continue with direct assignment
            
            page.wait_for_timeout(1000)
            page.evaluate(f"""
                const dateField = document.querySelector('#ddate');
                if (dateField) {{
                    dateField.value = '{formatted_date}';
                    dateField.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    dateField.dispatchEvent(new Event('change', {{ bubbles: true }}));
                    dateField.dispatchEvent(new Event('blur', {{ bubbles: true }}));
                }}
            """)
            
            # Verify date setting
            page.wait_for_timeout(1000)
            actual_date = page.evaluate("document.querySelector('#ddate').value")
            if actual_date and actual_date.strip():
                self.logger.info(f"         Date set: {actual_date}")
            else:
                self.logger.warning(f"         Date field empty, continuing...")
            
            # Final cleanup and submit search
            page.evaluate("""
                const allOverlays = document.querySelectorAll('[id*="overlay"], [class*="overlay"], .overlaybg1, #overlaybg1, #overlaybgg1');
                allOverlays.forEach(overlay => {
                    if (overlay) {
                        overlay.style.display = 'none';
                        overlay.style.visibility = 'hidden';
                        overlay.style.zIndex = '-1000';
                    }
                });
            """)
            page.wait_for_timeout(1000)
            
            try:
                page.click('[value="Search"]', timeout=5000)
                self.logger.info(f"    Search submitted successfully")
            except Exception as e:
                self.logger.error(f"    Search submission failed: {e}")
                return False
            
            page.wait_for_timeout(15000)
            
            # Verify results page loaded
            try:
                page.wait_for_selector('.fltResult', timeout=10000)
                self.logger.info(f"    Results page loaded successfully")
                return True
            except:
                self.logger.error(f"    Results page failed to load - URL: {page.url}")
                return False
                
        except Exception as e:
            self.logger.error(f"    Search error: {e}")
            return False

    def _select_city(self, page: Page, field_type: str, city_name: str) -> bool:
        """Select FROM/TO city using autocomplete dropdown"""
        try:
            # Field mappings
            input_id = '#FromSector_show' if field_type.lower() == 'from' else '#Editbox13_show'
            autocomplete_container = '#fromautoFill' if field_type.lower() == 'from' else '#toautoFill'
            
            # Clear and focus field
            page.evaluate(f"document.querySelector('{input_id}').value = ''")
            page.wait_for_timeout(500)
            
            # Different click strategies for EaseMyTrip's event handlers
            if field_type.lower() == 'from':
                # FROM field: Native Playwright click
                page.click(input_id, timeout=8000)
            else:
                # TO field: JavaScript click (bypasses overlays)
                page.evaluate(f"document.querySelector('{input_id}').click()")
            
            page.wait_for_timeout(1000)
            
            # Type city name and detect autocomplete
            suggestions_found = False
            for i, char in enumerate(city_name):
                page.keyboard.type(char)
                page.wait_for_timeout(300)
                
                # Check for suggestions every 3 characters
                if i >= 2 and (i + 1) % 2 == 0:
                    has_suggestions = page.evaluate(f"""
                        () => {{
                            const container = document.querySelector('{autocomplete_container}');
                            if (!container || container.style.display === 'none') return false;
                            
                            const suggestions = container.querySelectorAll('li, .city-option, .suggestion, a');
                            const validSuggestions = Array.from(suggestions).filter(s => 
                                s.offsetHeight > 0 && s.textContent.trim().length > 0
                            );
                            
                            const cityLower = '{city_name}'.toLowerCase();
                            return validSuggestions.some(s => {{
                                const cityPart = s.textContent.trim().split('(')[0].trim().toLowerCase();
                                return cityPart.includes(cityLower) || cityLower.includes(cityPart);
                            }});
                        }}
                    """)
                    
                    if has_suggestions:
                        suggestions_found = True
                        break
            
            # Select from autocomplete or try fallback
            return self._select_from_autocomplete(page, city_name, input_id, autocomplete_container, field_type, suggestions_found)
            
        except Exception as e:
            self.logger.error(f"         {field_type.upper()} city selection error: {e}")
            return False

    def _select_from_autocomplete(self, page: Page, city_name: str, input_id: str, autocomplete_container: str, field_type: str, suggestions_found: bool) -> bool:
        """Select city from autocomplete dropdown with fallback strategy"""
        page.wait_for_timeout(1000)
        
        # Create city variations
        city_variations = self._get_city_variations(city_name)
        
        # Try main selection
        if suggestions_found:
            result = self._attempt_city_selection(page, city_variations, autocomplete_container)
            if result['success']:
                return self._finalize_selection(page, result, input_id, field_type)
        
        # Fallback attempt
        fallback_result = self._try_fallback_selection(page, city_variations, autocomplete_container)
        if fallback_result['success']:
            return self._finalize_selection(page, fallback_result, input_id, field_type)
        
        self.logger.error(f"         {field_type.upper()} city selection failed for '{city_name}'")
        return False

    def _get_city_variations(self, city_name: str) -> list:
        """Generate city name variations for matching"""
        variations = [city_name, city_name.lower(), city_name.upper(), city_name.title()]
        return variations

    def _attempt_city_selection(self, page: Page, city_variations: list, autocomplete_container: str) -> dict:
        """Select best matching city from autocomplete suggestions"""
        return page.evaluate(f"""
            () => {{
                const cityVariations = {city_variations};
                const container = document.querySelector('{autocomplete_container}');
                if (!container) return {{success: false, error: 'No container'}};
                
                const suggestions = container.querySelectorAll('li, .city-option, .suggestion, a, div');
                const validSuggestions = Array.from(suggestions).filter(s => 
                    s.offsetHeight > 0 && s.textContent.trim().length > 0 && !s.getAttribute('aria-hidden')
                );
                
                if (validSuggestions.length === 0) return {{success: false, error: 'No suggestions'}};
                
                let bestMatch = null;
                let bestScore = 0;
                
                for (let item of validSuggestions) {{
                    const itemText = item.textContent.trim();
                    const cityInSuggestion = itemText.split('(')[0].trim();
                    
                    for (let variation of cityVariations) {{
                        let score = 0;
                        const suggestionLower = cityInSuggestion.toLowerCase();
                        const variationLower = variation.toLowerCase();
                        
                        if (suggestionLower === variationLower) score = 1000;
                        else if (suggestionLower.startsWith(variationLower)) score = 900;
                        else if (suggestionLower.includes(variationLower)) score = 700;
                        
                        if (score > bestScore) {{
                            bestScore = score;
                            bestMatch = {{element: item, text: itemText, score: score}};
                        }}
                    }}
                }}
                
                if (bestMatch && bestScore >= 700) {{
                    try {{
                        bestMatch.element.click();
                        return {{success: true, selectedText: bestMatch.text, matchScore: bestScore}};
                    }} catch(e) {{
                        return {{success: false, error: 'Click failed'}};
                    }}
                }}
                
                return {{success: false, error: 'No good match', bestScore: bestScore}};
            }}
        """)

    def _try_fallback_selection(self, page: Page, city_variations: list, autocomplete_container: str) -> dict:
        """Retry city selection for delayed autocomplete responses"""
        fallback_check = page.evaluate(f"""
            () => {{
                const container = document.querySelector('{autocomplete_container}');
                if (!container) return {{success: false}};
                
                const suggestions = container.querySelectorAll('li, .city-option, .suggestion, a, div');
                const validSuggestions = Array.from(suggestions).filter(s => 
                    s.offsetHeight > 0 && s.textContent.trim().length > 0
                );
                
                return {{success: validSuggestions.length > 0, count: validSuggestions.length}};
            }}
        """)
        
        if fallback_check.get('success'):
            page.wait_for_timeout(500)
            return self._attempt_city_selection(page, city_variations, autocomplete_container)
        
        return {'success': False, 'error': 'No fallback suggestions'}

    def _finalize_selection(self, page: Page, result: dict, input_id: str, field_type: str) -> bool:
        """Verify and confirm city selection in input field"""
        selected_text = result.get('selectedText', '')
        match_score = result.get('matchScore', 0)
        airport_code = self._extract_airport_code(selected_text)
        
        self.logger.info(f"         {field_type.upper()}: {selected_text} (Score: {match_score}, Airport: {airport_code or 'N/A'})")
        
        # Verify selection
        page.wait_for_timeout(800)
        final_value = page.evaluate(f"document.querySelector('{input_id}').value")
        if final_value and final_value.strip():
            self.logger.info(f"         {field_type.upper()} confirmed: {final_value}")
            return True
        
        return False

    def _extract_airport_code(self, selected_text: str) -> str:
        """Extract 3-letter airport code from selection text"""
        if not selected_text:
            return ""
        
        # Extract airport code from "CityName(CODE)" pattern
        match = re.search(r'\(([A-Z]{3})\)', selected_text)
        if match:
            return match.group(1)
        
        # If no airport code found, return empty string
        return ""

    def _format_date_for_input(self, date_str: str) -> str:
        """Convert YYYY-MM-DD to DD/MM/YYYY format"""
        year, month, day = date_str.split('-')
        return f"{day}/{month}/{year}"

    def _count_visible_flights(self, page: Page) -> int:
        """Count flights that are actually visible in the UI"""
        try:
            return page.evaluate("""
                () => {
                    let visibleCount = 0;
                    
                    try {
                        const flightElements = document.querySelectorAll('.fltResult[ng-if="dataToBindOutbound!=null"]');
                        
                        flightElements.forEach((element) => {
                            const computedStyle = getComputedStyle(element);
                            const isDisplayed = computedStyle.display !== 'none';
                            const isVisible = computedStyle.visibility !== 'hidden';
                            const hasOpacity = computedStyle.opacity !== '0';
                            const hasSize = element.offsetHeight > 0 && element.offsetWidth > 0;
                            const notHidden = !element.hidden;
                            const notNgHide = !element.classList.contains('ng-hide');
                            
                            const isTrulyVisible = isDisplayed && isVisible && hasOpacity && hasSize && notHidden && notNgHide;
                            
                            if (isTrulyVisible) {
                                visibleCount++;
                            }
                        });
                        
                    } catch (e) {
                        console.error('Error in flight counting:', e);
                    }
                    
                    return visibleCount;
                }
            """)
        except Exception as e:
            self.logger.error(f"Error counting visible flights: {e}")
            return 0

    def _apply_pure_ui_filters(self, page: Page, config: TestConfig):
        """Apply stops and price filters with proper timing"""
        try:
            self.logger.info(f"     Applying UI filters...")
            page.wait_for_timeout(5000)
            
            # Apply both price and stops filters directly
            self.logger.info(f"        Applying UI filters: {config.stops_filter} + ₹{config.price_min:,}-₹{config.price_max:,}")
            
            # Step 1: Apply stops filter
            self.logger.info(f"            1. Setting stops filter: {config.stops_filter}")
            stops_success = self._apply_stops_filter(page, config.stops_filter)
            if not stops_success:
                self.logger.warning(f"            → Stops filter may not have applied correctly")
                return
            
            # Step 2: Apply price filter 
            page.wait_for_timeout(2000)  # Wait for stops filter to settle
            self.logger.info(f"            2. Dragging price slider handles: ₹{config.price_min:,}-₹{config.price_max:,}")
            
            price_result = self._drag_price_slider_handles(page, config.price_min, config.price_max)
            if not price_result.get("success"):
                self.logger.warning(f"            → Price slider dragging failed")
                return
            
            # Step 3: Wait for filtering to complete
            page.wait_for_timeout(3000)
            
            # Update config with actual slider values
            actual_min = price_result["actual_min"]
            actual_max = price_result["actual_max"]
            
            if actual_min != config.price_min or actual_max != config.price_max:
                self.logger.info(f"            → UPDATED PRICE RANGE: Using ₹{actual_min:,}-₹{actual_max:,} (slider precision limitation)")
                self.logger.info(f"            → All subsequent filtering will use the actual slider values")
                
                # Update config for subsequent operations
                config.price_min = actual_min
                config.price_max = actual_max
                
                self.logger.info(f"    Updated config will be used for validation and reporting")
            
            self.logger.info(f"            → UI interaction complete - both filters applied")
            
            # Wait for filtering to stabilize
            page.wait_for_timeout(8000)
            
            # Extra wait for dynamic filtering
            page.wait_for_timeout(5000)
            
            self.logger.info(f"    All UI filters applied")
            
        except Exception as e:
            self.logger.error(f"    UI filter error: {e}")

    def _drag_price_slider_handles(self, page: Page, min_price: int, max_price: int):
        """Drag price slider handles and return actual values set"""
        try:
            # Get slider info and calculate positions
            slider_info = page.evaluate(f"""
                () => {{
                    const slider = document.getElementById('slider-range');
                    if (!slider) return {{success: false, error: 'Slider not found'}};
                    
                    const $slider = $(slider);
                    const sliderMin = $slider.slider('option', 'min') || 0;
                    const sliderMax = $slider.slider('option', 'max') || 50000;
                    const sliderWidth = slider.offsetWidth;
                    
                    const targetMin = Math.max({min_price}, sliderMin);
                    const targetMax = Math.min({max_price}, sliderMax);
                    
                    const minPercent = ((targetMin - sliderMin) / (sliderMax - sliderMin)) * 100;
                    const maxPercent = ((targetMax - sliderMin) / (sliderMax - sliderMin)) * 100;
                    
                    return {{
                        success: true,
                        sliderMin, sliderMax, sliderWidth,
                        targetMin, targetMax, minPercent, maxPercent
                    }};
                }}
            """)
            
            if not slider_info.get('success'):
                return {"success": False}
            
            # Get slider handles
            slider = page.locator("#slider-range")
            handles = slider.locator(".ui-slider-handle")
            
            if handles.count() != 2:
                return {"success": False}
            
            min_handle = handles.nth(0)
            max_handle = handles.nth(1)
            
            # Calculate target positions
            slider_box = slider.bounding_box()
            min_target_x = slider_box['x'] + (slider_info['minPercent'] / 100) * slider_info['sliderWidth']
            max_target_x = slider_box['x'] + (slider_info['maxPercent'] / 100) * slider_info['sliderWidth']
            
            # Drag minimum handle
            min_handle_box = min_handle.bounding_box()
            min_handle.hover()
            page.mouse.down()
            page.mouse.move(min_target_x, min_handle_box['y'] + min_handle_box['height'] / 2)
            page.mouse.up()
            page.wait_for_timeout(500)
            
            # Drag maximum handle
            max_handle_box = max_handle.bounding_box()
            max_handle.hover()
            page.mouse.down()
            page.mouse.move(max_target_x, max_handle_box['y'] + max_handle_box['height'] / 2)
            page.mouse.up()
            page.wait_for_timeout(500)
            
            # Get final values and calculate differences
            final_values = page.evaluate("""
                () => {
                    const slider = document.getElementById('slider-range');
                    const values = $(slider).slider('values');
                    return {
                        values: values,
                        success: values && values.length === 2
                    };
                }
            """)
            
            if final_values.get('success'):
                actual_min = final_values['values'][0]
                actual_max = final_values['values'][1]
                
                # Calculate and log differences
                min_diff = actual_min - min_price
                max_diff = actual_max - max_price
                
                self.logger.info(f"                → Requested: ₹{min_price:,} - ₹{max_price:,}")
                self.logger.info(f"                → Actual: ₹{actual_min:,} - ₹{actual_max:,}")
                self.logger.info(f"                → Difference: MIN {min_diff:+,} | MAX {max_diff:+,}")
                
                return {
                    "success": True,
                    "actual_min": actual_min,
                    "actual_max": actual_max,
                    "requested_min": min_price,
                    "requested_max": max_price
                }
            else:
                self.logger.error(f"                → Slider verification failed")
                return {"success": False}
                
        except Exception as e:
            self.logger.error(f"                → Slider error: {e}")
            return {"success": False}
    
    def _apply_stops_filter(self, page: Page, stops_filter: str):
        """Apply stops filter by checking/unchecking checkboxes"""
        try:
            # Map stops filter to checkbox
            stops_mapping = {
                'Non Stop': 'chkNonStop',
                'Non-stop': 'chkNonStop',  # Handle hyphenated version
                'Nonstop': 'chkNonStop',   # Handle single word version
                '1 Stop': 'chkOneStop', 
                '1-stop': 'chkOneStop',    # Handle hyphenated version
                '2+ Stop': 'chkTwoStop',
                '2+ Stops': 'chkTwoStop',  # Handle plural version
                '2-stop': 'chkTwoStop'     # Handle hyphenated version
            }
            
            target_checkbox_id = stops_mapping.get(stops_filter)
            if not target_checkbox_id:
                self.logger.error(f"                Unknown stops filter: '{stops_filter}'. Available options: {list(stops_mapping.keys())}")
                return False
            
            self.logger.info(f"                Target checkbox: {target_checkbox_id} (keep this CHECKED)")
            
            all_checkboxes = ['chkNonStop', 'chkOneStop', 'chkTwoStop']
            
            # Uncheck non-target checkboxes
            for checkbox_id in all_checkboxes:
                if checkbox_id != target_checkbox_id:
                    is_checked = page.evaluate(f"() => document.getElementById('{checkbox_id}')?.checked")
                    if is_checked:
                        page.locator(f"#{checkbox_id}").click(force=True, timeout=5000)
                        self.logger.info(f"                → Unchecked {checkbox_id}")
                        page.wait_for_timeout(1000)
            
            # Ensure target checkbox is checked
            target_checked = page.evaluate(f"() => document.getElementById('{target_checkbox_id}')?.checked")
            if target_checked:
                self.logger.info(f"                → {target_checkbox_id} already checked ")
            else:
                page.locator(f"#{target_checkbox_id}").click(force=True, timeout=5000)
                self.logger.info(f"                → Checked {target_checkbox_id} ")
                page.wait_for_timeout(1000)
            
            page.wait_for_timeout(3000)  # Wait for stops filtering to complete
            return True
            
        except Exception as e:
            self.logger.error(f"                Stops filter error: {e}")
            return False

    def _extract_filtered_flights_only(self, page: Page, config: TestConfig) -> List[Dict[str, Any]]:
        """Extract only flights visible in UI after filtering"""
        try:
            page.wait_for_timeout(5000)
            
            # Extract visible flights from UI
            extraction_result = page.evaluate("""
                () => {
                    const result = { visibleFlights: [], totalDOMFlights: 0 };
                    
                    try {
                        const flightElements = document.querySelectorAll('.fltResult[ng-if="dataToBindOutbound!=null"]');
                        result.totalDOMFlights = flightElements.length;
                        
                        flightElements.forEach((element) => {
                            const computedStyle = getComputedStyle(element);
                            const isDisplayed = computedStyle.display !== 'none';
                            const isVisible = computedStyle.visibility !== 'hidden';
                            const hasOpacity = computedStyle.opacity !== '0';
                            const hasSize = element.offsetHeight > 0 && element.offsetWidth > 0;
                            const notHidden = !element.hidden;
                            const notNgHide = !element.classList.contains('ng-hide');
                            
                            const isTrulyVisible = isDisplayed && isVisible && hasOpacity && hasSize && notHidden && notNgHide;
                            
                            if (isTrulyVisible) {
                                const price = parseInt(element.getAttribute('price')) || 0;
                                const stop = element.getAttribute('stop') || '';
                                const aircode = element.getAttribute('aircode') || '';
                                const fromCode = element.getAttribute('og') || 'N/A';
                                const toCode = element.getAttribute('ds') || 'N/A';
                                const flightNumber = element.getAttribute('fn') || 'N/A';
                                const deptm = element.getAttribute('deptm') || 'N/A';
                                const arrtm = element.getAttribute('arrtm') || 'N/A';
                                
                                // Convert stop code to readable format
                                let stopType = 'Unknown';
                                if (stop === '0') stopType = 'Non-stop';
                                else if (stop === '1') stopType = '1 Stop';
                                else if (stop === '2') stopType = '2+ Stop';
                                
                                // Convert airline code to name
                                let airline = 'Unknown';
                                if (aircode === '6E') airline = 'IndiGo';
                                else if (aircode === 'AI') airline = 'Air India';
                                else if (aircode === 'QP') airline = 'AkasaAir';
                                else if (aircode === 'SG') airline = 'SpiceJet';
                                else if (aircode === 'UK') airline = 'Vistara';
                                else if (aircode === 'G8') airline = 'GoAir';
                                else if (aircode === 'IX') airline = 'Air India Express';
                                else airline = aircode;
                                
                                const fullFlightNumber = aircode && flightNumber ? `${aircode}${flightNumber}` : flightNumber;
                                
                                const flight = {
                                    index: result.visibleFlights.length + 1,
                                    airline: airline,
                                    flight_number: fullFlightNumber,
                                    price: price,
                                    stops: stopType,
                                    from_code: fromCode,
                                    to_code: toCode,
                                    route: fromCode + ' -> ' + toCode,
                                    departure_time: deptm,
                                    arrival_time: arrtm,
                                    raw_stop: stop,
                                    raw_aircode: aircode
                                };
                                
                                result.visibleFlights.push(flight);
                            }
                        });
                        
                    } catch (e) {
                        result.error = e.message;
                    }
                    
                    return result;
                }
            """)
            
            visible_flights = extraction_result.get('visibleFlights', [])
            total_dom_flights = extraction_result.get('totalDOMFlights', 0)
            
            if len(visible_flights) == 0:
                self.logger.warning(f"No flights visible in UI - filtering may have hidden all flights")
                return []
            
            self.logger.info(f"Extracted {len(visible_flights)} visible flights from {total_dom_flights} total")
            
            return visible_flights
            
        except Exception as e:
            self.logger.error(f"Error extracting flights: {e}")
            return []
            
    def _validate_extracted_flights_meet_criteria(self, flights: List[Dict[str, Any]], config: TestConfig) -> Dict[str, Any]:
        """Validate extracted flights meet filter criteria"""
        if not flights:
            self.logger.info("    VALIDATION: No flights to validate")
            return {'total_flights': 0, 'valid_flights': 0, 'invalid_flights': 0, 'validation_passed': True}
        
        try:
            # Define stops equivalencies for quick lookup
            stops_map = {
                'Non-stop': 'Non-stop', 'Nonstop': 'Non-stop',
                '1 Stop': '1 Stop', '1-stop': '1 Stop', 'One Stop': '1 Stop',
                '2+ Stop': '2+ Stop', '2 Stop': '2+ Stop', '2 Stops': '2+ Stop', 'Two Stop': '2+ Stop'
            }
            expected_stop = stops_map.get(config.stops_filter, config.stops_filter)
            
            # Validate flights using list comprehensions
            valid_flights = [
                f for f in flights 
                if (config.price_min <= f.get('price', 0) <= config.price_max and 
                    stops_map.get(f.get('stops', ''), f.get('stops', '')) == expected_stop)
            ]
            
            invalid_flights = [f for f in flights if f not in valid_flights]
            validation_passed = len(invalid_flights) == 0
            
            # Log summary
            total = len(flights)
            valid_count = len(valid_flights)
            invalid_count = len(invalid_flights)
            
            status = " PASSED" if validation_passed else " FAILED"
            self.logger.info(f"    VALIDATION {status}: {valid_count}/{total} valid | Price: ₹{config.price_min:,}-₹{config.price_max:,} | Stops: {config.stops_filter}")
            
            # Log invalid flights (only if failures exist and count is reasonable)
            if invalid_count > 0 and invalid_count <= 3:
                for i, flight in enumerate(invalid_flights[:3], 1):
                    price_issue = f"price ₹{flight.get('price', 0)}" if not (config.price_min <= flight.get('price', 0) <= config.price_max) else ""
                    stops_issue = f"stops '{flight.get('stops', '')}'" if stops_map.get(flight.get('stops', ''), flight.get('stops', '')) != expected_stop else ""
                    issues = " | ".join(filter(None, [price_issue, stops_issue]))
                    self.logger.error(f"        Invalid {i}: {flight.get('airline', '')} - {issues}")
            elif invalid_count > 3:
                self.logger.error(f"        {invalid_count} invalid flights (showing summary only)")
            
            return {
                'total_flights': total,
                'valid_flights': valid_count,
                'invalid_flights': invalid_count,
                'validation_passed': validation_passed
            }
            
        except Exception as e:
            self.logger.error(f"    Validation error: {e}")
            return {'total_flights': len(flights), 'valid_flights': 0, 'invalid_flights': len(flights), 'validation_passed': False}  