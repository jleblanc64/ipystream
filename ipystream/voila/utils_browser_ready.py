from IPython.display import display, HTML
import ipywidgets as widgets


def on_browser_ready(f):
    """
    Utility function that triggers a callback function once the browser has loaded and JavaScript is executing.

    Args:
        f: A function to call when browser is ready. No arguments are passed.

    Usage:
        def my_callback():
            print("Browser is ready!")

        on_browser_ready(my_callback)
    """
    # Create counter with unique CSS class - HIDDEN
    counter = widgets.IntText(value=0, description="Count:")
    counter.add_class("js-counter-widget")
    counter.layout.display = "none"

    # Observer that calls the user's function
    def on_counter_change(change):
        f()

    counter.observe(on_counter_change, names="value")

    # JavaScript that manipulates the widget directly - status HIDDEN
    js_code = HTML(
        """
        <div id="js-status" style="display: none;">
            <strong>JS Status:</strong> <span id="status-msg">Attempting...</span>
        </div>
        <script>
        (function() {
            console.log('[JS] Starting widget manipulation');
            const statusMsg = document.getElementById('status-msg');
            
            function tryUpdateWidget() {
                // Find the input element with our custom class
                const counterWidget = document.querySelector('.js-counter-widget');
                console.log('[JS] Counter widget element:', counterWidget);
                
                if (counterWidget) {
                    // Find the actual input inside it
                    const input = counterWidget.querySelector('input[type="number"]');
                    console.log('[JS] Input element:', input);
                    
                    if (input) {
                        // Get current value and increment
                        const currentValue = parseInt(input.value) || 0;
                        const newValue = currentValue + 1;
                        
                        console.log('[JS] Current value:', currentValue);
                        console.log('[JS] Setting to:', newValue);
                        
                        // Update the value
                        input.value = newValue;
                        
                        // Trigger all possible events
                        input.dispatchEvent(new Event('input', { bubbles: true }));
                        input.dispatchEvent(new Event('change', { bubbles: true }));
                        input.dispatchEvent(new KeyboardEvent('keyup', { bubbles: true }));
                        input.blur();
                        input.focus();
                        
                        console.log('[JS] Events dispatched');
                        statusMsg.textContent = '✓ Widget updated to ' + newValue;
                        statusMsg.style.color = 'green';
                        
                        return true;
                    }
                }
                
                statusMsg.textContent = '✗ Widget not found yet';
                statusMsg.style.color = 'orange';
                return false;
            }
            
            // Try multiple times with delays
            let attempts = 0;
            const maxAttempts = 10;
            
            const interval = setInterval(function() {
                attempts++;
                console.log('[JS] Attempt', attempts);
                
                if (tryUpdateWidget() || attempts >= maxAttempts) {
                    clearInterval(interval);
                    if (attempts >= maxAttempts) {
                        statusMsg.textContent = '✗ Failed after ' + maxAttempts + ' attempts';
                        statusMsg.style.color = 'red';
                    }
                }
            }, 500);
            
        })();
        </script>
    """
    )

    display(counter)
    display(js_code)
