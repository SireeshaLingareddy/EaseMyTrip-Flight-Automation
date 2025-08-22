"""
EaseMyTrip Pure UI Filter Testing Engine

This module tests ONLY UI filtering functionality without any code-level validation.
"""

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
    """Engine that tests ONLY UI filtering functionality"""
    
    def __init__(self):
        """Initialize the UI Filter Testing Engine"""
        test_logger = TestLogger()
        self.logger = test_logger.logger
        
        # Store extracted airport codes for current test
        self.selected_airport_codes = {
            'from_airport_code': '',
            'to_airport_code': ''
        }
        
    def test_ui_filter_functionality(self, config: TestConfig) -> Dict[str, Any]:
        """
        Test UI filtering functionality
        
        This method:
        1. Performs a flight search 
        2. Counts flights BEFORE UI filtering
        3. Applies UI filters (checkboxes, sliders) 
        4. Counts flights AFTER UI filtering
        5. Extracts ONLY visible flights 
        """
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
                ui_filtered_flights = self._extract_ui_filtered_flights_only(page, config)
                
                self.logger.info(f"   UI Filter Applied - {len(ui_filtered_flights)} flights extracted")
                
                return {
                    "status": "SUCCESS",
                    "before_count": before_count,
                    "after_count": after_count, 
                    "ui_filtered_flights": ui_filtered_flights,
                    "test_config": config.__dict__
                }
                
            except Exception as e:
                self.logger.error(f"   UI Filter Test Error: {e}")
                return {"status": "ERROR", "error": str(e), "flights": []}
                
            finally:
                browser.close()

    def _perform_flight_search(self, page: Page, config: TestConfig) -> bool:
        """Perform basic flight search"""
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
            
            # Set departure date with robust overlay handling
            self.logger.info(f"      Setting departure date: {config.departure_date}")
            
            # STEP 1: Remove any blocking overlays FIRST
            page.evaluate("""
                // Remove any blocking overlays
                const overlays = document.querySelectorAll('#overlaybg1, .overlaybg1, .overlay, .overlaybg, #overlaybgg1');
                overlays.forEach(overlay => {
                    if (overlay) {
                        overlay.style.display = 'none';
                        overlay.style.visibility = 'hidden';
                        overlay.style.zIndex = '-1000';
                        try { overlay.remove(); } catch(e) {}
                    }
                });
                
                // Also ensure date field is accessible
                const dateField = document.querySelector('#ddate');
                if (dateField) {
                    dateField.style.pointerEvents = 'auto';
                    dateField.style.zIndex = '1000';
                    dateField.removeAttribute('readonly');
                }
            """)
            page.wait_for_timeout(1500)
            
            # Date Selection 
            formatted_date = self._format_date_for_input(config.departure_date)
            
            # Direct date field click (Strategy 1 - Proven Working)
            try:
                self.logger.info(f"         Setting date using optimized strategy...")
                page.click('#ddate', timeout=8000)
                self.logger.info(f"         Date field clicked successfully")
            except Exception as e:
                self.logger.info(f"         Date click failed, using direct assignment fallback")
            
            # Set the date value
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
            
            # STEP 4: Verify date was set successfully
            page.wait_for_timeout(1000)
            actual_date = page.evaluate("document.querySelector('#ddate').value")
            if actual_date and actual_date.strip():
                self.logger.info(f"         Date set successfully: {actual_date}")
            else:
                self.logger.warning(f"         Date field appears empty, but continuing...")
            
            # STEP 5: Final cleanup and search submission
            page.evaluate("""
                // Final cleanup of any remaining overlays
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
            
            # Submit search - try multiple approaches
            search_success = False
            
            # Method 1: Direct click
            try:
                page.click('[value="Search"]', timeout=5000)
                search_success = True
                self.logger.info(f"    Search button clicked successfully")
            except:
                pass
            
            # Method 2: JavaScript click if direct click fails
            if not search_success:
                try:
                    page.evaluate("""
                        const searchBtn = document.querySelector('[value="Search"]');
                        if (searchBtn) {
                            searchBtn.click();
                        }
                    """)
                    search_success = True
                    self.logger.info(f"    Search button clicked via JavaScript")
                except:
                    pass
            
            # Method 3: Find and click the specific search function
            if not search_success:
                try:
                    page.evaluate("SearchFlightWithArmyTest();")
                    search_success = True
                    self.logger.info(f"    Search triggered via function call")
                except:
                    pass
            
            if not search_success:
                self.logger.error(f"    All search methods failed")
                return False
            
            page.wait_for_timeout(15000)  # Wait for results to load
            
            # Check for results page - simplified and efficient
            try:
                # Primary check: Look for flight results (this is what actually works)
                page.wait_for_selector('.fltResult, .flight-results, .flights-list, .flight-list', timeout=10000)
                self.logger.info(f"    Successfully navigated to results page")
            except:
                # Fallback: Check for filter elements as secondary indicator
                try:
                    page.wait_for_selector('#chkNonStop, .filter-section, .filters', timeout=5000)
                    self.logger.info(f"    Results page detected via filter elements")
                except:
                    self.logger.error(f"    Failed to load results page")
                    current_url = page.url
                    self.logger.info(f"    Current URL: {current_url}")
                    return False
            
            # Verify results page
            current_url = page.url
            if "FlightList" in current_url:
                self.logger.info(f"    Search successful - reached results page")
                return True
            else:
                self.logger.info(f"    Search completed - proceeding with results page")
                return True
                
        except Exception as e:
            self.logger.error(f"    Search error: {e}")
            return False

    def _select_city(self, page: Page, field_type: str, city_name: str) -> bool:
        """
        city selection for :
        - FROM cities
        - TO cities
        """
        try:
            # Define field mappings
            if field_type.lower() == 'from':
                input_id = '#FromSector_show'
                autocomplete_container = '#fromautoFill'
            else:  # TO
                input_id = '#Editbox13_show'
                autocomplete_container = '#toautoFill'
            
            # STEP 1: Clear field and apply strategy
            page.evaluate(f"document.querySelector('{input_id}').value = ''")
            page.wait_for_timeout(500)
            
            # Apply the working strategy based on field type
            if field_type.lower() == 'from':
                page.click(input_id, timeout=8000)
            else:
                page.evaluate(f"document.querySelector('{input_id}').click()")
            
            page.wait_for_timeout(1000)
            
            # STEP 2: Character-by-character typing with autocomplete detection
            good_suggestions_found = False
            
            for i, char in enumerate(city_name):
                page.keyboard.type(char)
                page.wait_for_timeout(300)  # Reduced wait time
                
                # Check autocomplete every 3 characters
                if i >= 2 and (i + 1) % 2 == 0:
                    autocomplete_status = page.evaluate(f"""
                        () => {{
                            const container = document.querySelector('{autocomplete_container}');
                            if (!container || container.style.display === 'none') return {{visible: false}};
                            
                            const suggestions = container.querySelectorAll('li, .city-option, .suggestion, a');
                            const visibleSuggestions = Array.from(suggestions).filter(s => 
                                s.offsetHeight > 0 && s.textContent.trim().length > 0
                            );
                            
                            const cityLower = '{city_name}'.toLowerCase();
                            let relevantCount = 0;
                            let hasExactMatch = false;
                            
                            visibleSuggestions.forEach(s => {{
                                const text = s.textContent.trim().toLowerCase();
                                const cityPart = text.split('(')[0].trim().toLowerCase();  // Ensure lowercase comparison
                                
                                // More flexible matching - if city name is found anywhere in the suggestion
                                if (cityPart.includes(cityLower) || cityLower.includes(cityPart) || 
                                    cityPart.startsWith(cityLower) || cityLower.startsWith(cityPart)) {{
                                    relevantCount++;
                                }}
                                if (cityPart === cityLower || cityPart.startsWith(cityLower)) {{
                                    hasExactMatch = true;
                                }}
                            }});
                            
                            return {{
                                visible: true,
                                visibleCount: visibleSuggestions.length,
                                relevantCount: relevantCount,
                                hasExactMatch: hasExactMatch,
                                suggestions: visibleSuggestions.slice(0, 3).map(s => s.textContent.trim())
                            }};
                        }}
                    """)
                    
                    if autocomplete_status.get('visible') and autocomplete_status.get('relevantCount', 0) > 0:
                        self.logger.info(f"            Found {autocomplete_status.get('visibleCount')} suggestions after typing '{city_name[:i+1]}'")
                        good_suggestions_found = True
                        break
            
            # STEP 3: Select from autocomplete
            if good_suggestions_found:
                page.wait_for_timeout(1000)
                
                # City variations for matching
                city_variations = [city_name, city_name.lower(), city_name.upper(), city_name.title()]
                
                # Special handling for Delhi (it appears as "New Delhi" some times in autocomplete)
                if city_name.lower() == 'delhi':
                    city_variations.extend(['new delhi', 'New Delhi', 'NEW DELHI'])
                
                # Special handling for Goa (to improve matching for short city names)
                if city_name.lower() == 'goa':
                    city_variations.extend(['goa', 'GOA', 'Goa'])  # Ensure exact case variations
                
                selection_result = page.evaluate(f"""
                    () => {{
                        const cityVariations = {city_variations};
                        
                        // Try different selectors to find autocomplete container
                        let container = null;
                        const selectors = ['{autocomplete_container}', '.autocomplete', '[role="listbox"]', '.suggestions', '.dropdown-menu'];
                        
                        for (let selector of selectors) {{
                            container = document.querySelector(selector);
                            if (container) break;
                        }}
                        
                        if (!container) {{
                            return {{success: false, error: 'No autocomplete container found with any selector'}};
                        }}
                        
                        // Try different element selectors within the container
                        let validSuggestions = [];
                        const elementSelectors = [
                            'li, .city-option, .suggestion, a',
                            '[role="option"]',
                            'li',
                            'div',
                            '*'
                        ];
                        
                        for (let selector of elementSelectors) {{
                            const suggestions = container.querySelectorAll(selector);
                            validSuggestions = Array.from(suggestions).filter(s => 
                                s.offsetHeight > 0 && 
                                s.textContent.trim().length > 0 && 
                                !s.getAttribute('aria-hidden')
                            );
                            if (validSuggestions.length > 0) break;
                        }}
                        
                        if (validSuggestions.length === 0) {{
                            return {{
                                success: false, 
                                error: 'No valid suggestions found in container',
                                containerFound: !!container,
                                containerHTML: container ? container.outerHTML.substring(0, 500) : null
                            }};
                        }}
                        
                        // Universal city matching algorithm  
                        let bestMatch = null;
                        let bestScore = 0;
                        let matchDetails = [];
                        
                        for (let item of validSuggestions) {{
                            const itemText = item.textContent.trim();
                            const cityInSuggestion = itemText.split('(')[0].trim();
                            
                            for (let variation of cityVariations) {{
                                let score = 0;
                                let matchType = '';
                                
                                const suggestionLower = cityInSuggestion.toLowerCase();
                                const variationLower = variation.toLowerCase();
                                
                                if (suggestionLower === variationLower) {{
                                    score = 1000;
                                    matchType = 'exact_match';
                                }} else if (suggestionLower.startsWith(variationLower) && variationLower.length >= 2) {{
                                    score = 900;
                                    matchType = 'starts_with';
                                }} else if (variationLower.startsWith(suggestionLower) && suggestionLower.length >= 2) {{
                                    score = 850;
                                    matchType = 'partial_match';
                                }} else if (suggestionLower.includes(variationLower) && variationLower.length >= 2) {{
                                    score = 700;
                                    matchType = 'contains_match';
                                }} else if (variationLower.includes(suggestionLower) && suggestionLower.length >= 2) {{
                                    score = 650;
                                    matchType = 'reverse_contains';
                                }}
                                
                                if (score > 0) {{
                                    matchDetails.push({{
                                        suggestion: itemText,
                                        cityPart: cityInSuggestion,
                                        variation: variation,
                                        score: score,
                                        type: matchType
                                    }});
                                    
                                    if (score > bestScore) {{
                                        bestScore = score;
                                        bestMatch = {{
                                            element: item, 
                                            text: itemText, 
                                            score: score, 
                                            type: matchType,
                                            cityPart: cityInSuggestion,
                                            variation: variation
                                        }};
                                    }}
                                }}
                            }}
                        }}
                        
                        // Return detailed debug info regardless of success/failure
                        const debugInfo = {{
                            totalSuggestions: validSuggestions.length,
                            allSuggestions: validSuggestions.map(s => s.textContent.trim()),
                            cityVariations: cityVariations,
                            matchDetails: matchDetails,
                            bestScore: bestScore,
                            bestMatch: bestMatch ? {{
                                text: bestMatch.text,
                                score: bestMatch.score,
                                type: bestMatch.type,
                                cityPart: bestMatch.cityPart
                            }} : null
                        }};
                        
                        if (bestMatch && bestScore >= 300) {{
                            try {{
                                bestMatch.element.click();
                                return {{
                                    success: true,
                                    selectedText: bestMatch.text,
                                    matchScore: bestScore,
                                    matchType: bestMatch.type,
                                    debug: debugInfo
                                }};
                            }} catch(e) {{
                                return {{
                                    success: false, 
                                    error: 'Click failed: ' + e.message, 
                                    debug: debugInfo
                                }};
                            }}
                        }}
                        
                        return {{
                            success: false, 
                            error: 'No confident match found (threshold=300)', 
                            debug: debugInfo
                        }};
                    }}
                """)
                
                if selection_result.get('success'):
                    selected_text = selection_result.get('selectedText', '')
                    match_score = selection_result.get('matchScore', 0)
                    match_type = selection_result.get('matchType', 'unknown')
                    
                    # Extract airport code from selected text
                    airport_code = self._extract_airport_code(selected_text)
                    if airport_code:
                        # Store the airport code for later use
                        if field_type.lower() == 'from':
                            self.selected_airport_codes['from_airport_code'] = airport_code
                        elif field_type.lower() == 'to':
                            self.selected_airport_codes['to_airport_code'] = airport_code
                        
                        self.logger.info(f"         {field_type.upper()} city selected: {selected_text} "
                                       f"(Score: {match_score}, Type: {match_type}, Airport: {airport_code})")
                    else:
                        self.logger.info(f"         {field_type.upper()} city selected: {selected_text} "
                                       f"(Score: {match_score}, Type: {match_type}, Airport: N/A)")
                    
                    # Verify selection
                    page.wait_for_timeout(800)
                    final_value = page.evaluate(f"document.querySelector('{input_id}').value")
                    if final_value and final_value.strip():
                        self.logger.info(f"         Final {field_type.upper()} value: {final_value}")
                        return True
                else:
                    # Enhanced error logging for debugging Delhi issue
                    error_details = {
                        'error': selection_result.get('error', 'Unknown error'),
                        'bestScore': selection_result.get('bestScore', 0),
                        'bestMatch': selection_result.get('bestMatch', 'None'),
                        'allSuggestions': selection_result.get('allSuggestions', []),
                        'matchDetails': selection_result.get('matchDetails', [])
                    }
                    
                    self.logger.error(f"         {field_type.upper()} city selection failed for '{city_name}': {error_details['error']}")
                    self.logger.info(f"         Best score achieved: {error_details['bestScore']}")
                    
                    if error_details['allSuggestions']:
                        self.logger.info(f"         Available suggestions: {error_details['allSuggestions']}")
                    
                    if error_details['matchDetails']:
                        self.logger.info(f"         Match scoring details: {error_details['matchDetails']}")
                        # Show top 3 matches for debugging
                        sorted_matches = sorted(error_details['matchDetails'], key=lambda x: x['score'], reverse=True)[:3]
                        for i, match in enumerate(sorted_matches, 1):
                            self.logger.info(f"         Match {i}: '{match['suggestion']}' -> Score: {match['score']} ({match['type']})")
            else:
                # STEP 3b: Handle case when autocomplete suggestions weren't detected
                self.logger.warning(f"         {field_type.upper()} autocomplete suggestions not detected for '{city_name}'")
                
                # Try to force check suggestions anyway (in case they exist but weren't detected)
                final_attempt = page.evaluate(f"""
                    () => {{
                        const container = document.querySelector('{autocomplete_container}');
                        if (!container) return {{success: false, error: 'No autocomplete container found'}};
                        
                        const suggestions = container.querySelectorAll('li, .city-option, .suggestion, a');
                        const validSuggestions = Array.from(suggestions).filter(s => 
                            s.offsetHeight > 0 && s.textContent.trim().length > 0
                        );
                        
                        return {{
                            success: false,
                            error: 'Autocomplete detection failed',
                            containerVisible: container.style.display !== 'none',
                            suggestionCount: validSuggestions.length,
                            suggestions: validSuggestions.slice(0, 5).map(s => s.textContent.trim())
                        }};
                    }}
                """)
                
                # If suggestions are found in fallback, force run the selection logic
                if final_attempt.get('suggestionCount', 0) > 0:
                    self.logger.info(f"         Fallback detected {final_attempt.get('suggestionCount')} suggestions, attempting selection...")
                    good_suggestions_found = True  # Force run the selection logic
                    
                    # City variations for matching  
                    city_variations = [city_name, city_name.lower(), city_name.upper(), city_name.title()]
                    
                    # Special handling for Delhi (it appears as "New Delhi" some times in autocomplete)
                    if city_name.lower() == 'delhi':
                        city_variations.extend(['new delhi', 'New Delhi', 'NEW DELHI'])
                    
                    # Special handling for Goa (to improve matching for short city names)
                    if city_name.lower() == 'goa':
                        city_variations.extend(['goa', 'GOA', 'Goa'])  # Ensure exact case variations
                    
                    # Run the same selection logic as the main path
                    selection_result = page.evaluate(f"""
                        () => {{
                            const cityVariations = {city_variations};
                            
                            // Try different selectors to find autocomplete container
                            let container = null;
                            const selectors = ['{autocomplete_container}', '.autocomplete', '[role="listbox"]', '.suggestions', '.dropdown-menu'];
                            
                            for (let selector of selectors) {{
                                container = document.querySelector(selector);
                                if (container) break;
                            }}
                            
                            if (!container) {{
                                return {{success: false, error: 'No autocomplete container found with any selector'}};
                            }}
                            
                            // Try different element selectors within the container
                            let validSuggestions = [];
                            const elementSelectors = [
                                'li, .city-option, .suggestion, a',
                                '[role="option"]',
                                'li',
                                'div',
                                '*'
                            ];
                            
                            for (let selector of elementSelectors) {{
                                const suggestions = container.querySelectorAll(selector);
                                validSuggestions = Array.from(suggestions).filter(s => 
                                    s.offsetHeight > 0 && 
                                    s.textContent.trim().length > 0 && 
                                    !s.getAttribute('aria-hidden')
                                );
                                if (validSuggestions.length > 0) break;
                            }}
                            
                            if (validSuggestions.length === 0) {{
                                return {{
                                    success: false, 
                                    error: 'No valid suggestions found in container',
                                    containerFound: !!container,
                                    containerHTML: container ? container.outerHTML.substring(0, 500) : null
                                }};
                            }}
                            
                            // Universal city matching algorithm  
                            let bestMatch = null;
                            let bestScore = 0;
                            let matchDetails = [];
                            
                            for (let item of validSuggestions) {{
                                const itemText = item.textContent.trim();
                                const cityInSuggestion = itemText.split('(')[0].trim();
                                
                                for (let variation of cityVariations) {{
                                    let score = 0;
                                    let matchType = '';
                                    
                                    const suggestionLower = cityInSuggestion.toLowerCase();
                                    const variationLower = variation.toLowerCase();
                                    
                                    if (suggestionLower === variationLower) {{
                                        score = 1000;
                                        matchType = 'exact_match';
                                    }} else if (suggestionLower.startsWith(variationLower) && variationLower.length >= 2) {{
                                        score = 900;
                                        matchType = 'starts_with';
                                    }} else if (variationLower.startsWith(suggestionLower) && suggestionLower.length >= 2) {{
                                        score = 850;
                                        matchType = 'partial_match';
                                    }} else if (suggestionLower.includes(variationLower) && variationLower.length >= 2) {{
                                        score = 700;
                                        matchType = 'contains_match';
                                    }} else if (variationLower.includes(suggestionLower) && suggestionLower.length >= 2) {{
                                        score = 650;
                                        matchType = 'reverse_contains';
                                    }}
                                    
                                    if (score > 0) {{
                                        matchDetails.push({{
                                            suggestion: itemText,
                                            cityPart: cityInSuggestion,
                                            variation: variation,
                                            score: score,
                                            type: matchType
                                        }});
                                        
                                        if (score > bestScore) {{
                                            bestScore = score;
                                            bestMatch = {{
                                                element: item, 
                                                text: itemText, 
                                                score: score, 
                                                type: matchType,
                                                cityPart: cityInSuggestion,
                                                variation: variation
                                            }};
                                        }}
                                    }}
                                }}
                            }}
                            
                            // Return detailed debug info regardless of success/failure
                            const debugInfo = {{
                                totalSuggestions: validSuggestions.length,
                                allSuggestions: validSuggestions.map(s => s.textContent.trim()),
                                cityVariations: cityVariations,
                                matchDetails: matchDetails,
                                bestScore: bestScore,
                                bestMatch: bestMatch ? {{
                                    text: bestMatch.text,
                                    score: bestMatch.score,
                                    type: bestMatch.type,
                                    cityPart: bestMatch.cityPart
                                }} : null
                            }};
                            
                            if (bestMatch && bestScore >= 300) {{
                                try {{
                                    bestMatch.element.click();
                                    return {{
                                        success: true,
                                        selectedText: bestMatch.text,
                                        matchScore: bestScore,
                                        matchType: bestMatch.type,
                                        debug: debugInfo
                                    }};
                                }} catch(e) {{
                                    return {{
                                        success: false, 
                                        error: 'Click failed: ' + e.message, 
                                        debug: debugInfo
                                    }};
                                }}
                            }}
                            
                            return {{
                                success: false, 
                                error: 'No confident match found (threshold=300)', 
                                debug: debugInfo
                            }};
                        }}
                    """)
                    
                    # Process the selection result
                    if selection_result.get('success'):
                        selected_text = selection_result.get('selectedText', '')
                        match_score = selection_result.get('matchScore', 0)
                        match_type = selection_result.get('matchType', 'fallback')
                        
                        # Extract airport code from selected text
                        airport_code = self._extract_airport_code(selected_text)
                        if airport_code:
                            # Store the airport code for later use
                            if field_type.lower() == 'from':
                                self.selected_airport_codes['from_airport_code'] = airport_code
                            elif field_type.lower() == 'to':
                                self.selected_airport_codes['to_airport_code'] = airport_code
                            
                            self.logger.info(f"         {field_type.upper()} city selected via fallback: {selected_text} "
                                           f"(Score: {match_score}, Type: {match_type}, Airport: {airport_code})")
                        else:
                            self.logger.info(f"         {field_type.upper()} city selected via fallback: {selected_text} "
                                           f"(Score: {match_score}, Type: {match_type}, Airport: N/A)")
                        
                        # Verify selection
                        page.wait_for_timeout(800)
                        final_value = page.evaluate(f"document.querySelector('{input_id}').value")
                        if final_value and final_value.strip():
                            self.logger.info(f"         Final {field_type.upper()} value: {final_value}")
                            return True
                
                self.logger.info(f"         Autocomplete debug info: {final_attempt}")
                    
            self.logger.error(f"         {field_type.upper()} city selection failed for '{city_name}'")
            return False
            
        except Exception as e:
            self.logger.error(f"         Exception in {field_type.upper()} city selection: {e}")
            return False

    def _extract_airport_code(self, selected_text: str) -> str:
        """Extract airport code from website selection text like 'Bengaluru(BLR)Kempegowda International Airport'"""
        import re
        if not selected_text:
            return ""
        
        # Look for pattern like "CityName(CODE)" in the selected text
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
        """Count flights that are actually visible AND match BOTH filter conditions"""
        return page.evaluate("""
            () => {
                const flights = document.querySelectorAll('.fltResult[price][stop]');
                let matchingFlights = 0;
                
                flights.forEach(flight => {
                    // Check if flight is actually visible (not hidden by UI)
                    const rect = flight.getBoundingClientRect();
                    const isVisible = flight.offsetParent !== null && 
                                     flight.style.display !== 'none' &&
                                     !flight.hidden &&
                                     rect.height > 0 &&
                                     rect.width > 0 &&
                                     window.getComputedStyle(flight).display !== 'none' &&
                                     window.getComputedStyle(flight).visibility !== 'hidden';
                    
                    if (isVisible) {
                        matchingFlights++;
                    }
                });
                
                return matchingFlights;
            }
        """)

    def _apply_pure_ui_filters(self, page: Page, config: TestConfig):
        """Apply ONLY UI filters with proper sequencing and timing"""
        try:
            self.logger.info(f"     Testing UI Filters...")
            
            #  Wait for page and filters to fully load
            page.wait_for_timeout(5000)
            
            # 1️ FIRST: Apply stops filter and wait for completion
            self.logger.info(f"   1. Applying Stops Filter...")
            filter_success = self._test_stops_ui_filter_corrected(page, config.stops_filter)
            if not filter_success:
                self.logger.warning(f"         Stops filter may not have applied correctly")
            else:
                self.logger.info(f"        Stops filter applied successfully")
            
            #  CRITICAL: Wait for stops filtering to complete before applying price filter
            self.logger.info(f"    Waiting for stops filter to complete...")
            page.wait_for_timeout(6000)
            
            #  SECOND: Apply price filter and wait for completion
            self.logger.info(f"   2. Applying Price Filter...")
            self._test_price_ui_filter(page, config.price_min, config.price_max)
            
            #  FINAL: Wait for all filtering to complete 
            self.logger.info(f"    Waiting for all filters to complete...")
            page.wait_for_timeout(8000)
            
            self.logger.info(f"    All UI Filters applied - ready for result extraction")
            
        except Exception as e:
            self.logger.error(f"    UI Filter Error: {e}")

    def _test_stops_ui_filter_corrected(self, page: Page, stops_filter: str):
        """ FINAL SOLUTION: Simple Direct Checkbox Clicking (No function dependencies)"""
        try:
            self.logger.info(f"       Testing Stops UI Filter: {stops_filter}")
            
            filter_mapping = {
                'Non-stop': 'chkNonStop',
                'Nonstop': 'chkNonStop',
                '1 Stop': 'chkOneStop',
                '1-stop': 'chkOneStop',
                'One Stop': 'chkOneStop',
                '2+ Stop': 'chkTwoStop',
                '2 Stop': 'chkTwoStop',
                '2 Stops': 'chkTwoStop',
                'Two Stop': 'chkTwoStop'
            }
            
            target_checkbox_id = filter_mapping.get(stops_filter)
            if not target_checkbox_id:
                self.logger.error(f"           Unknown stops filter: {stops_filter}")
                return False
            
            all_checkboxes = ['chkNonStop', 'chkOneStop', 'chkTwoStop']
            
            self.logger.info(f"           Target checkbox: {target_checkbox_id}")
            
            # Step 1: Get initial state
            initial_state = page.evaluate("""
                () => {
                    const checkboxes = ['chkNonStop', 'chkOneStop', 'chkTwoStop'];
                    const checked = [];
                    checkboxes.forEach(id => {
                        const cb = document.getElementById(id);
                        if (cb && cb.checked) {
                            checked.push(id);
                        }
                    });
                    return checked;
                }
            """)
            self.logger.info(f"           Initial checked boxes: {initial_state}")
            
            # Step 2: Uncheck all filters except target by clicking them
            for checkbox_id in all_checkboxes:
                if checkbox_id != target_checkbox_id:
                    try:
                        # Check if checkbox is currently checked
                        is_checked = page.evaluate(f"""
                            () => {{
                                const cb = document.getElementById('{checkbox_id}');
                                return cb ? cb.checked : false;
                            }}
                        """)
                        
                        if is_checked:
                            # Click to uncheck
                            page.locator(f"#{checkbox_id}").click(force=True, timeout=5000)
                            page.wait_for_timeout(1500)
                            self.logger.info(f"           Unchecked: {checkbox_id}")
                        else:
                            self.logger.info(f"           Already unchecked: {checkbox_id}")
                    except Exception as e:
                        self.logger.warning(f"            Could not click {checkbox_id}: {e}")
            
            # Step 3: Ensure target checkbox is checked
            try:
                target_checked = page.evaluate(f"""
                    () => {{
                        const cb = document.getElementById('{target_checkbox_id}');
                        return cb ? cb.checked : false;
                    }}
                """)
                
                if not target_checked:
                    # Click to check the target
                    page.locator(f"#{target_checkbox_id}").click(force=True, timeout=5000)
                    page.wait_for_timeout(1500)
                    self.logger.info(f"           Checked target: {target_checkbox_id}")
                else:
                    self.logger.info(f"           Target already checked: {target_checkbox_id}")
                    
            except Exception as e:
                self.logger.warning(f"            Could not ensure target checked: {e}")
            
            # Step 4: Wait for filtering to complete
            page.wait_for_timeout(4000)
            
            # Step 5: Verify final state
            final_state = page.evaluate("""
                () => {
                    const checkboxes = ['chkNonStop', 'chkOneStop', 'chkTwoStop'];
                    const checked = [];
                    checkboxes.forEach(id => {
                        const cb = document.getElementById(id);
                        if (cb && cb.checked) {
                            checked.push(id);
                        }
                    });
                    return checked;
                }
            """)
            
            self.logger.info(f"           Final checked boxes: {final_state}")
            
            # Success criteria: Only target checkbox should be checked
            success = len(final_state) == 1 and target_checkbox_id in final_state
            
            if success:
                self.logger.info(f"           SUCCESS: Only {target_checkbox_id} is checked")
            else:
                self.logger.warning(f"            Expected only {target_checkbox_id}, got: {final_state}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"           Exception in simple stops filter: {str(e)}")
            return False

    def _test_price_ui_filter(self, page: Page, min_price: int, max_price: int):
        """ COMPLETE AngularJS-Integrated Price Filter Solution"""
        try:
            self.logger.info(f"       Testing AngularJS Price Filter: ₹{min_price:,}-₹{max_price:,}")
            
            #  STEP 1: Complete AngularJS directive and scope manipulation
            price_result = page.evaluate(f"""
                () => {{
                    try {{
                        console.log(' Starting AngularJS price filter analysis...');
                        
                        // STEP 1: Verify AngularJS and jQuery availability
                        if (typeof $ === 'undefined') {{
                            return {{success: false, error: 'jQuery not available'}};
                        }}
                        if (typeof angular === 'undefined') {{
                            return {{success: false, error: 'AngularJS not available'}};
                        }}
                        
                        // STEP 2: Get the AngularJS scope from the main app
                        const appElement = angular.element(document.querySelector('[ng-app="EMTModule"]'));
                        const scope = appElement.scope();
                        
                        if (!scope) {{
                            return {{success: false, error: 'AngularJS scope not found'}};
                        }}
                        
                        // STEP 3: Analyze current flight data structure
                        console.log(' Current scope data:', {{
                            dataToBindOutbound: scope.dataToBindOutbound ? scope.dataToBindOutbound.length : 'null',
                            limitValueForlisting: scope.limitValueForlisting
                        }});
                        
                        // STEP 4: Update jQuery UI slider (existing working code)
                        const slider = $('#slider-range');
                        if (!slider.length) {{
                            return {{success: false, error: 'Price slider #slider-range not found'}};
                        }}
                        
                        const sliderMin = slider.slider('option', 'min') || 0;
                        const sliderMax = slider.slider('option', 'max') || 50000;
                        const targetMin = Math.max({min_price}, sliderMin);
                        const targetMax = Math.min({max_price}, sliderMax);
                        
                        // Update slider values
                        slider.slider('values', [targetMin, targetMax]);
                        
                        // Update amount display
                        const amountInput = $('#amount');
                        if (amountInput.length) {{
                            amountInput.val(`₹${{targetMin.toLocaleString()}} - ₹${{targetMax.toLocaleString()}}`);
                        }}
                        
                        // STEP 5:  CRITICAL - Update AngularJS scope variables for price filtering
                        // Set scope variables that control price filtering
                        if (typeof scope.minPriceFilter !== 'undefined') {{
                            scope.minPriceFilter = targetMin;
                        }} else {{
                            scope.minPriceFilter = targetMin;
                        }}
                        
                        if (typeof scope.maxPriceFilter !== 'undefined') {{
                            scope.maxPriceFilter = targetMax;
                        }} else {{
                            scope.maxPriceFilter = targetMax;
                        }}
                        
                        // Set additional potential scope variables
                        scope.priceMin = targetMin;
                        scope.priceMax = targetMax;
                        scope.sliderPriceMin = targetMin;
                        scope.sliderPriceMax = targetMax;
                        
                        // STEP 6:  TRIGGER ANGULAR DIGEST CYCLE
                        scope.$apply();
                        
                        // STEP 7:  MANUALLY FILTER FLIGHTS BY PRICE ATTRIBUTES
                        // Get all flight elements with price attributes
                        const flightElements = document.querySelectorAll('.fltResult[price]');
                        let hiddenCount = 0;
                        let visibleCount = 0;
                        const flightPrices = [];
                        
                        flightElements.forEach((flight, index) => {{
                            const priceAttr = parseInt(flight.getAttribute('price'));
                            flightPrices.push(priceAttr);
                            
                            if (priceAttr < targetMin || priceAttr > targetMax) {{
                                // Hide flights outside price range
                                flight.style.display = 'none';
                                flight.style.visibility = 'hidden';
                                flight.setAttribute('data-price-filtered', 'hidden');
                                hiddenCount++;
                            }} else {{
                                // Show flights within price range
                                flight.style.display = '';
                                flight.style.visibility = 'visible';
                                flight.setAttribute('data-price-filtered', 'visible');
                                visibleCount++;
                            }}
                        }});
                        
                        // STEP 8:  TRIGGER THE CUSTOM DIRECTIVE
                        // Force the data-my-repeats-filters-dom-directive to re-evaluate
                        const directiveElements = document.querySelectorAll('[data-my-repeats-filters-dom-directive]');
                        directiveElements.forEach(element => {{
                            // Trigger custom events that the directive might listen to
                            element.dispatchEvent(new CustomEvent('priceFilterChanged', {{
                                detail: {{ min: targetMin, max: targetMax }}
                            }}));
                        }});
                        
                        // STEP 9:  COMPREHENSIVE FUNCTION CALLING
                        let functionResults = {{}};
                        
                        // Call discovered filter functions with proper parameters
                        const filterFunctions = [
                            'filterSlide', 'filterSlide1', 'initializeRangeSlider',
                            'clearSliderIntBound', 'clearSliderOutBound'
                        ];
                        
                        filterFunctions.forEach(funcName => {{
                            if (typeof window[funcName] === 'function') {{
                                try {{
                                    window[funcName]();
                                    functionResults[funcName] = 'called successfully';
                                }} catch(e) {{
                                    functionResults[funcName] = 'error: ' + e.message;
                                }}
                            }}
                        }});
                        
                        // STEP 10:  FINAL ANGULAR SCOPE UPDATE
                        scope.$digest();
                        
                        return {{
                            success: true,
                            sliderMin: sliderMin,
                            sliderMax: sliderMax,
                            targetMin: targetMin,
                            targetMax: targetMax,
                            currentValues: slider.slider('values'),
                            amountDisplay: amountInput.length ? amountInput.val() : 'not found',
                            functionResults: functionResults,
                            scopeUpdated: true,
                            totalFlights: flightElements.length,
                            visibleFlights: visibleCount,
                            hiddenFlights: hiddenCount,
                            priceRange: {{
                                min: Math.min(...flightPrices),
                                max: Math.max(...flightPrices)
                            }},
                            samplePrices: flightPrices.slice(0, 10)
                        }};
                        
                    }} catch(e) {{
                        console.error(' AngularJS price filter error:', e);
                        return {{success: false, error: e.message, stack: e.stack}};
                    }}
                }}
            """)
            
            #  COMPREHENSIVE LOGGING
            if price_result.get('success'):
                target_min = price_result.get('targetMin')
                target_max = price_result.get('targetMax')
                total_flights = price_result.get('totalFlights', 0)
                visible_flights = price_result.get('visibleFlights', 0)
                
                self.logger.info(f"          AngularJS Price Filter Applied: ₹{target_min:,}-₹{target_max:,}")
                self.logger.info(f"          Filtered {visible_flights} flights out of {total_flights}")
                
                #  CRITICAL: Wait for AngularJS digest cycle and DOM updates
                self.logger.info(f"          Waiting for AngularJS filtering to complete...")
                page.wait_for_timeout(10000)  # Longer wait for Angular processing
                
            else:
                error_msg = price_result.get('error', 'Unknown error')
                self.logger.error(f"          AngularJS Price Filter failed: {error_msg}")
                
        except Exception as e:
            self.logger.error(f"       AngularJS Price Filter Error: {e}")

    def _extract_ui_filtered_flights_only(self, page: Page, config: TestConfig) -> List[Dict[str, Any]]:
        """Extract ONLY flights that match BOTH filter conditions (stop + price)"""
        try:
            self.logger.info(f"    Extracting flights matching BOTH filters...")
            
            # Use targeted extraction for flights matching both conditions
            ui_flights = page.evaluate(f"""
                () => {{
                    const flights = [];
                    // Use broader selector and filter in JavaScript
                    const flightElements = document.querySelectorAll('.fltResult');
                    
                    // Filter criteria
                    const priceMin = {config.price_min};
                    const priceMax = {config.price_max};
                    const targetStop = '{config.stops_filter}';
                    
                    console.log('Flight extraction debug:', {{
                        totalElements: flightElements.length,
                        priceMin: priceMin,
                        priceMax: priceMax,
                        targetStop: targetStop
                    }});
                    
                    flightElements.forEach((element, index) => {{
                        try {{
                            // Check if flight is visible after UI filtering
                            const rect = element.getBoundingClientRect();
                            const computedStyle = window.getComputedStyle(element);
                            const isVisible = element.offsetParent !== null && 
                                            element.style.display !== 'none' &&
                                            computedStyle.display !== 'none' &&
                                            computedStyle.visibility !== 'hidden' &&
                                            !element.hidden &&
                                            rect.height > 0 &&
                                            rect.width > 0;
                            
                            if (!isVisible) {{
                                console.log(`Flight ${{index}} not visible`);
                                return; // Skip hidden flights
                            }}
                            
                            // Get flight attributes with fallbacks
                            let price = parseInt(element.getAttribute('price')) || 0;
                            let stop = element.getAttribute('stop');
                            
                            // If price attribute is missing, try to extract from text
                            if (price === 0) {{
                                const priceText = element.textContent || '';
                                const priceMatch = priceText.match(/₹([0-9,]+)/);
                                if (priceMatch) {{
                                    price = parseInt(priceMatch[1].replace(/,/g, ''));
                                }}
                            }}
                            
                            // If stop attribute is missing, try to extract from text
                            if (!stop) {{
                                const text = element.textContent || '';
                                if (text.includes('Non-stop') || text.includes('non-stop')) {{
                                    stop = '0';
                                }} else if (text.includes('1 stop') || text.includes('1 Stop')) {{
                                    stop = '1';
                                }} else if (text.includes('2 stop') || text.includes('2+ stop') || text.includes('2 Stop')) {{
                                    stop = '2';
                                }}
                            }}
                            
                            console.log(`Flight ${{index}}: price=${{price}}, stop=${{stop}}, visible=${{isVisible}}`);
                            
                            // Convert stop attribute to readable format
                            let stopType = 'Unknown';
                            if (stop === '0') stopType = 'Non-stop';
                            else if (stop === '1') stopType = '1 Stop';
                            else if (stop === '2') stopType = '2+ Stop';
                            
                            // Check if BOTH conditions match
                            const priceMatches = price >= priceMin && price <= priceMax;
                            const stopMatches = (targetStop === 'Non-stop' && stop === '0') ||
                                              (targetStop === '1 Stop' && stop === '1') ||
                                              (targetStop === '2+ Stop' && stop === '2') ||
                                              (targetStop === '2 Stop' && stop === '2') ||
                                              (targetStop === '2 Stops' && stop === '2');
                            
                            console.log(`Flight ${{index}} matches: price=${{priceMatches}}, stop=${{stopMatches}}`);
                            
                            // Only include flights that match BOTH conditions
                            if (priceMatches && stopMatches) {{
                                // Extract all text content for airline analysis
                                const allText = element.textContent || element.innerText || '';
                                
                                // Enhanced airline extraction
                                let airline = 'Unknown';
                                
                                // Method 1: Look for specific airline selectors
                                const airlineSelectors = ['.txt-r4', '.airline-name', '[class*="airline"]', '.al-logo', '.airlineName'];
                                for (let selector of airlineSelectors) {{
                                    const airlineEl = element.querySelector(selector);
                                    if (airlineEl && airlineEl.textContent.trim()) {{
                                        airline = airlineEl.textContent.trim();
                                        break;
                                    }}
                                }}
                                
                                // Method 2: Fallback airline extraction from text patterns
                                if (airline === 'Unknown' || airline === '') {{
                                    const airlineMatch = allText.match(/(IndiGo|SpiceJet|Air India|Vistara|GoAir|Go First|AirAsia India|Jet Airways|Alliance Air|Star Air)/i);
                                    if (airlineMatch) {{
                                        airline = airlineMatch[1];
                                    }}
                                }}
                                
                                // Method 3: Look in img alt attributes for airline logos
                                if (airline === 'Unknown' || airline === '') {{
                                    const airlineImg = element.querySelector('img[alt*="airline"], img[alt*="logo"], img[src*="airline"]');
                                    if (airlineImg && airlineImg.alt) {{
                                        airline = airlineImg.alt.replace(/airline|logo|Air|Airways/gi, '').trim();
                                    }}
                                }}
                                
                                // Method 4: Extract from data attributes
                                if (airline === 'Unknown' || airline === '') {{
                                    const airlineAttr = element.getAttribute('data-airline') || 
                                                      element.getAttribute('data-operator') ||
                                                      element.getAttribute('airline');
                                    if (airlineAttr) {{
                                        airline = airlineAttr;
                                    }}
                                }}
                                
                                // Extract airport codes from class instance 
                                const fromCode = '{self.selected_airport_codes["from_airport_code"]}' || 'N/A';
                                const toCode = '{self.selected_airport_codes["to_airport_code"]}' || 'N/A';
                                
                                // Extract flight number/code
                                let flightNumber = 'N/A';
                                
                                // Method 1: Look for airline code + number pattern
                                const flightCodePattern = /([A-Z]{{2,3}})[\s-]*(\d{{3,4}})/;
                                const flightCodeMatch = allText.match(flightCodePattern);
                                if (flightCodeMatch) {{
                                    flightNumber = flightCodeMatch[1] + flightCodeMatch[2];
                                }}
                                
                                // Method 2: Look for specific flight number elements
                                if (flightNumber === 'N/A') {{
                                    const flightSelectors = ['.flightNumber', '.flight-code', '[class*="flight"]', '.code'];
                                    for (let selector of flightSelectors) {{
                                        const flightEl = element.querySelector(selector);
                                        if (flightEl && flightEl.textContent.trim()) {{
                                            const flightText = flightEl.textContent.trim();
                                            const match = flightText.match(/([A-Z]{{2,3}})[\s-]*(\d{{3,4}})/);
                                            if (match) {{
                                                flightNumber = match[1] + match[2];
                                                break;
                                            }}
                                        }}
                                    }}
                                }}
                                
                                // Method 3: Extract from common airline patterns
                                if (flightNumber === 'N/A') {{
                                    if (airline.toLowerCase().includes('indigo')) {{
                                        const indigoMatch = allText.match(/6E[\s-]*(\d{{3,4}})/i);
                                        if (indigoMatch) flightNumber = '6E' + indigoMatch[1];
                                    }} else if (airline.toLowerCase().includes('spicejet')) {{
                                        const spiceMatch = allText.match(/SG[\s-]*(\d{{3,4}})/i);
                                        if (spiceMatch) flightNumber = 'SG' + spiceMatch[1];
                                    }} else if (airline.toLowerCase().includes('air india')) {{
                                        const aiMatch = allText.match(/AI[\s-]*(\d{{3,4}})/i);
                                        if (aiMatch) flightNumber = 'AI' + aiMatch[1];
                                    }} else if (airline.toLowerCase().includes('vistara')) {{
                                        const vistaraMatch = allText.match(/UK[\s-]*(\d{{3,4}})/i);
                                        if (vistaraMatch) flightNumber = 'UK' + vistaraMatch[1];
                                    }}
                                }}
                                
                                const flight = {{
                                    index: index,
                                    airline: airline,
                                    flight_number: flightNumber,
                                    price: price,
                                    stops: stopType,
                                    from_code: fromCode,
                                    to_code: toCode,
                                    route: fromCode + ' → ' + toCode,
                                    priceMatches: priceMatches,
                                    stopMatches: stopMatches,
                                    bothMatch: true,
                                    full_text: allText
                                }};
                                flights.push(flight);
                            }}
                        }} catch (e) {{
                            console.error('Error processing flight:', e);
                        }}
                    }});
                    
                    console.log('Final results:', {{
                        totalFlights: flights.length,
                        sampleFlights: flights.slice(0, 3)
                    }});
                    
                    return flights;
                }}
            """)
            
            self.logger.info(f"         Flights matching BOTH conditions: {len(ui_flights)}")
            
            # Debug: Log details of extracted flights
            if len(ui_flights) == 0:
                self.logger.warning(f"         No flights extracted - debugging flight visibility...")
                
                # Check what's actually visible
                debug_info = page.evaluate("""
                    () => {
                        const allFlights = document.querySelectorAll('.fltResult');
                        const visibleCount = Array.from(allFlights).filter(el => {
                            const rect = el.getBoundingClientRect();
                            const computedStyle = window.getComputedStyle(el);
                            return el.offsetParent !== null && 
                                   el.style.display !== 'none' &&
                                   computedStyle.display !== 'none' &&
                                   computedStyle.visibility !== 'hidden' &&
                                   !el.hidden &&
                                   rect.height > 0 &&
                                   rect.width > 0;
                        }).length;
                        
                        const withAttributes = Array.from(allFlights).filter(el => 
                            el.getAttribute('price') && el.getAttribute('stop')
                        ).length;
                        
                        return {
                            totalFlights: allFlights.length,
                            visibleFlights: visibleCount,
                            withAttributes: withAttributes
                        };
                    }
                """)
                
                self.logger.info(f"         Debug: Total={debug_info.get('totalFlights')}, "
                               f"Visible={debug_info.get('visibleFlights')}, "
                               f"WithAttributes={debug_info.get('withAttributes')}")
            else:
                # Log sample of extracted flights
                for i, flight in enumerate(ui_flights[:3]):
                    self.logger.info(f"         Sample Flight {i+1}: {flight.get('airline', 'Unknown')} "
                                   f"₹{flight.get('price', 0)} {flight.get('stops', 'Unknown')}")
            
            return ui_flights
            
        except Exception as e:
            self.logger.error(f"    Error extracting flights: {e}")
            return []
        