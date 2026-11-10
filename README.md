# Calculator

Requires Python 3.8+.

1. Extract the ZIP or clone the repository, then open a terminal in the folder containing `server.py`.
2. Run `python server.py`.
3. Open http://localhost:8080 in your browser.
4. Try these sums, pressing **C** between each:

   - `2 + 3 + (4 * 5)` → **25**
   - `2 + 3 * 4` → **14**
   - `(2 + 3) * 4` → **20**
   - `8 / 2 * 2` → **8**
   - `0.1 + 0.2` → **0.3**
   - `4 / (2 - 2)` → **Cannot divide by zero**

5. In another terminal in the same folder, run `python -m unittest -v`. Expect **62 tests, OK**.
6. Press **Ctrl+C** in the server terminal to stop.
