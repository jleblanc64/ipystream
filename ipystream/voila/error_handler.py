def html(e, KERNEL_CLEANUP_TIMEOUT_SEC):
    if "HTTP 503" in str(e):
        return f"""
                <script>document.body.innerHTML = "";</script>
                <html>
                  <head>
                    <title>App Limit Reached</title>
                    <style>
                      body {{ font-family: Arial, sans-serif; background: #fafafa; color: #333; text-align: center; padding-top: 10%; }}
                      .box {{ display: inline-block; background: white; border: 1px solid #ccc; border-radius: 12px; padding: 30px 50px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
                      h1 {{ color: #c0392b; }}
                    </style>
                  </head>
                  <body>
                    <div class="box">
                      <h1>App Already Open</h1>
                      <p>You have duplicated pages of the app opened.<br>
                         Please re-use an existing tab or close extra ones.</p>
                    </div>
                  </body>
                </html>
                """
    elif "HTTP 504" in str(e):
        return f"""
                <script>document.body.innerHTML = "";</script>
                <html>
                  <head>
                    <title>App Limit Reached</title>
                    <style>
                      body {{ font-family: Arial, sans-serif; background: #fafafa; color: #333; text-align: center; padding-top: 10%; }}
                      .box {{ display: inline-block; background: white; border: 1px solid #ccc; border-radius: 12px; padding: 30px 50px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
                      h1 {{ color: #c0392b; }}
                    </style>
                  </head>
                  <body>
                    <div class="box">
                      <h1>No more app capacity available</h1>
                      <p>You or other users are using all the server capacity.<br>
                         Please re-use or close opened app tabs.</p>
                      <p>Closed pages kernels are cleaned up after {KERNEL_CLEANUP_TIMEOUT_SEC} seconds</p>
                    </div>
                  </body>
                </html>
                """

    elif "HTTP 404" in str(e):
        return """
            <html>
            <head><title>Not Found</title></head>
            <body style="font-family:sans-serif;text-align:center;margin-top:10%;">
                <h1>404: Page Not Found</h1>
                <p>The page you're looking for doesn't exist or the session expired.</p>
                <button onclick="goHome()">Go Home</button>
            
                <script>
                  function goHome() {{
                    const query = window.location.search;
                    const target = '/' + (query ? query : '');
                    window.location.href = target;
                  }}
                </script>
            </body>
            </html>
            """

    return None