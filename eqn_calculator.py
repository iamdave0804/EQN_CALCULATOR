from __future__ import annotations

from decimal import Decimal, InvalidOperation, getcontext
from html import escape
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse
import os
import threading
import webbrowser


getcontext().prec = 50


def decimal_abs(value: Decimal) -> Decimal:
    return value.copy_abs()


def format_decimal(value: Decimal, digits: int = 12) -> str:
    if value == 0:
        return "0"
    text = format(value, f".{digits}g")
    if "E" in text:
        text = text.replace("E", "e")
    return text


def solve_by_gauss_jordan(augmented_matrix: list[list[Decimal]]) -> tuple[str, list[Decimal]]:
    size = len(augmented_matrix)
    epsilon = Decimal("1e-28")

    matrix = [row[:] for row in augmented_matrix]
    pivot_columns: list[int] = []
    row = 0

    for col in range(size):
        pivot_row = None
        pivot_value = Decimal("0")

        for candidate in range(row, size):
            candidate_value = decimal_abs(matrix[candidate][col])
            if candidate_value > pivot_value:
                pivot_value = candidate_value
                pivot_row = candidate

        if pivot_row is None or pivot_value <= epsilon:
            continue

        if pivot_row != row:
            matrix[row], matrix[pivot_row] = matrix[pivot_row], matrix[row]

        pivot = matrix[row][col]
        matrix[row] = [value / pivot for value in matrix[row]]

        for other_row in range(size):
            if other_row == row:
                continue
            factor = matrix[other_row][col]
            if decimal_abs(factor) <= epsilon:
                continue
            matrix[other_row] = [
                matrix[other_row][index] - factor * matrix[row][index]
                for index in range(size + 1)
            ]

        pivot_columns.append(col)
        row += 1
        if row == size:
            break

    for current_row in range(size):
        left_side_zero = all(decimal_abs(matrix[current_row][col]) <= epsilon for col in range(size))
        if left_side_zero and decimal_abs(matrix[current_row][size]) > epsilon:
            return "no_solution", []

    if len(pivot_columns) < size:
        return "infinite", []

    solution = [Decimal("0")] * size
    for current_row, col in enumerate(pivot_columns):
        solution[col] = matrix[current_row][size]

    return "unique", solution


def example_matrix(count: int) -> list[list[Decimal]]:
    matrix = []
    for row in range(count):
        values = [Decimal("0")] * (count + 1)
        for col in range(count):
            if row == col:
                values[col] = Decimal(str(row + 2))
            else:
                values[col] = Decimal(str((row + col) % 3)) / Decimal("2")
        values[count] = Decimal(str((row + 1) * 3))
        matrix.append(values)
    return matrix


def build_matrix_html(count: int, values: list[list[str]] | None = None) -> str:
    rows = []
    for row in range(count):
        cells = []
        for col in range(count + 1):
            value = ""
            if values and row < len(values) and col < len(values[row]):
                value = escape(values[row][col])
            cells.append(
                f'<input class="cell" name="a_{row}_{col}" inputmode="decimal" autocomplete="off" value="{value}" />'
            )
        rows.append(
            f'<div class="row"><div class="row-label">{row + 1}행</div>'
            + "".join(cells)
            + '<div class="equals">=</div><div class="b-label">b</div></div>'
        )
    headers = "".join(f'<div class="head">x{index + 1}</div>' for index in range(count))
    return f"""
    <div class="matrix-wrap">
      <div class="row header-row">
        <div class="row-label">식</div>
        {headers}
        <div class="equals">=</div><div class="b-label">b</div>
      </div>
      {''.join(rows)}
    </div>
    """


def parse_matrix(form: dict[str, list[str]], count: int) -> list[list[Decimal]]:
    matrix: list[list[Decimal]] = []
    for row in range(count):
        row_values: list[Decimal] = []
        for col in range(count + 1):
            key = f"a_{row}_{col}"
            raw_value = form.get(key, [""])[0].strip()
            if not raw_value:
                raise ValueError(f"{row + 1}행 {col + 1}열 값이 비어 있습니다.")
            try:
                row_values.append(Decimal(raw_value))
            except InvalidOperation as exc:
                raise ValueError(f"{row + 1}행 {col + 1}열 값 '{raw_value}'는 숫자가 아닙니다.") from exc
        matrix.append(row_values)
    return matrix


def render_page(
    count: int = 2,
    result_html: str = "",
    values: list[list[str]] | None = None,
    result_class: str = "",
) -> str:
    count = min(max(count, 2), 6)
    matrix_html = build_matrix_html(count, values)
    options = "".join(
        f'<option value="{number}"{" selected" if number == count else ""}>{number}</option>'
        for number in range(2, 7)
    )
    return f"""
    <!doctype html>
    <html lang="ko">
    <head>
      <meta charset="utf-8" />
      <meta name="viewport" content="width=device-width, initial-scale=1" />
      <title>연립방정식 계산기</title>
      <style>
        :root {{
          --bg: #f4f7fb;
          --card: rgba(255, 255, 255, 0.88);
          --line: #d7deea;
          --text: #0f172a;
          --muted: #5b6476;
          --accent: #2563eb;
          --accent-2: #0ea5e9;
        }}
        * {{ box-sizing: border-box; }}
        body {{
          margin: 0;
          font-family: Inter, Pretendard, system-ui, -apple-system, BlinkMacSystemFont, sans-serif;
          color: var(--text);
          background:
            radial-gradient(circle at top left, rgba(37,99,235,.14), transparent 30%),
            radial-gradient(circle at top right, rgba(14,165,233,.12), transparent 24%),
            linear-gradient(180deg, #eef3ff, var(--bg));
          min-height: 100vh;
        }}
        .wrap {{ max-width: 1180px; margin: 0 auto; padding: 36px 20px 48px; }}
        .hero {{
          display: grid;
          grid-template-columns: 1.4fr .9fr;
          gap: 20px;
          align-items: stretch;
          margin-bottom: 18px;
        }}
        .panel, .card {{
          background: var(--card);
          border: 1px solid rgba(255,255,255,.55);
          box-shadow: 0 18px 45px rgba(15, 23, 42, 0.08);
          backdrop-filter: blur(12px);
          border-radius: 22px;
        }}
        .panel {{ padding: 26px; }}
        h1 {{ margin: 0 0 10px; font-size: clamp(32px, 4vw, 52px); line-height: 1.02; letter-spacing: -0.03em; }}
        .desc {{ margin: 0; color: var(--muted); font-size: 15px; line-height: 1.7; max-width: 58ch; }}
        .badge {{
          display: inline-flex; align-items: center; gap: 8px;
          padding: 8px 12px; border-radius: 999px; background: rgba(37,99,235,.10);
          color: var(--accent); font-weight: 700; font-size: 13px; margin-bottom: 14px;
        }}
        .side {{ padding: 22px; display: grid; gap: 12px; }}
        .metric {{ padding: 16px; border-radius: 18px; border: 1px solid var(--line); background: rgba(255,255,255,.72); }}
        .metric .k {{ font-size: 12px; color: var(--muted); text-transform: uppercase; letter-spacing: .12em; }}
        .metric .v {{ margin-top: 8px; font-size: 20px; font-weight: 800; }}
        .controls, .card {{ padding: 18px; }}
        .toolbar {{ display: flex; flex-wrap: wrap; gap: 12px; align-items: end; margin-bottom: 16px; }}
        label {{ display: grid; gap: 6px; font-size: 13px; font-weight: 700; color: var(--muted); }}
        select, input.cell, button {{ font: inherit; }}
        select {{
          border: 1px solid var(--line); border-radius: 14px; background: white; color: var(--text);
          padding: 12px 14px; min-width: 120px; outline: none;
        }}
        button {{
          border: 0; border-radius: 14px; padding: 12px 16px; cursor: pointer; font-weight: 800;
          transition: transform .15s ease, box-shadow .15s ease, opacity .15s ease;
        }}
        button:hover {{ transform: translateY(-1px); }}
        .primary {{ background: linear-gradient(135deg, var(--accent), var(--accent-2)); color: white; box-shadow: 0 14px 28px rgba(37,99,235,.25); }}
        .ghost {{ background: white; color: var(--text); border: 1px solid var(--line); }}
        .matrix-wrap {{ overflow-x: auto; padding-bottom: 4px; }}
        .row {{ display: grid; grid-template-columns: 72px repeat({count}, 1fr) 34px 24px; gap: 8px; align-items: center; margin-bottom: 10px; }}
        .header-row {{ margin-bottom: 12px; }}
        .row-label, .head, .equals, .b-label {{ text-align: center; font-weight: 800; color: var(--muted); }}
        .head {{ padding: 0 8px; }}
        input.cell {{
          width: 100%; min-width: 90px; padding: 13px 12px; border-radius: 14px;
          border: 1px solid var(--line); background: rgba(255,255,255,.95); outline: none;
          box-shadow: inset 0 1px 0 rgba(255,255,255,.65);
        }}
        input.cell:focus, select:focus {{ border-color: rgba(37,99,235,.65); box-shadow: 0 0 0 4px rgba(37,99,235,.12); }}
        .result {{
          margin-top: 18px; padding: 18px; border-radius: 18px; border: 1px solid var(--line);
          background: rgba(255,255,255,.82); min-height: 74px; white-space: pre-wrap; line-height: 1.7;
        }}
        .result.ok {{ border-color: rgba(34,197,94,.35); }}
        .result.warn {{ border-color: rgba(245,158,11,.35); }}
        .result.err {{ border-color: rgba(239,68,68,.35); }}
        .actions {{ display: flex; gap: 10px; flex-wrap: wrap; }}
        .footer-note {{ margin-top: 12px; color: var(--muted); font-size: 13px; }}
        @media (max-width: 900px) {{
          .hero {{ grid-template-columns: 1fr; }}
          .row {{ grid-template-columns: 64px repeat({count}, minmax(86px, 1fr)) 30px 22px; }}
        }}
      </style>
    </head>
    <body>
      <div class="wrap">
        <div class="hero">
          <section class="panel">
            <div class="badge">가우스-조르당 소거법</div>
            <h1>연립방정식 계산기</h1>
            <p class="desc">
              2개부터 6개까지 미지수를 선택하고 계수와 우변 상수를 입력하면, 표준 라이브러리만으로
              브라우저 UI에서 바로 풉니다. 부분 피벗팅과 Decimal 고정 정밀도를 사용해 수치 오차를 줄였습니다.
            </p>
          </section>
          <aside class="panel side">
            <div class="metric"><div class="k">지원 범위</div><div class="v">2 ~ 6 미지수</div></div>
            <div class="metric"><div class="k">수치 방식</div><div class="v">Decimal + 부분 피벗팅</div></div>
            <div class="metric"><div class="k">실행 방식</div><div class="v">python eqn_calculator.py</div></div>
          </aside>
        </div>

        <section class="card controls">
          <form method="post" action="/solve">
            <div class="toolbar">
              <label>
                미지수 개수
                <select name="count">
                  {options}
                </select>
              </label>
              <div class="actions">
                <button class="primary" type="submit">계산하기</button>
                <button class="ghost" type="submit" name="action" value="example">예시 채우기</button>
                <button class="ghost" type="submit" name="action" value="clear">초기화</button>
              </div>
            </div>
            {matrix_html}
          </form>
          <div class="footer-note">입력이 비어 있으면 어느 칸이 문제인지 바로 알려줍니다.</div>
        </section>

                <section class="result {escape(result_class)}">{result_html}</section>
      </div>
      <script>
        const select = document.querySelector('select[name="count"]');
                select.addEventListener('change', () => {{
                    window.location = '/?count=' + select.value;
                }});
      </script>
    </body>
    </html>
    """


class EquationRequestHandler(BaseHTTPRequestHandler):
    server_version = "EquationCalculator/1.0"

    def log_message(self, format: str, *args: object) -> None:
        return

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path not in {"/", ""}:
            self.send_error(HTTPStatus.NOT_FOUND)
            return

        count = 2
        query = parse_qs(parsed.query)
        if query.get("count"):
            try:
                count = int(query["count"][0])
            except ValueError:
                count = 2
        self._respond_html(render_page(count=count))

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path != "/solve":
            self.send_error(HTTPStatus.NOT_FOUND)
            return

        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length).decode("utf-8")
        form = parse_qs(body)

        try:
            count = int(form.get("count", ["2"])[0])
        except ValueError:
            count = 2
        count = min(max(count, 2), 6)

        action = form.get("action", [""])[0]
        if action == "clear":
            self._respond_html(render_page(count=count, result_html="입력을 모두 지웠습니다.", result_class="warn"))
            return

        if action == "example":
            values = [[format(value, "g") for value in row] for row in example_matrix(count)]
            self._respond_html(
                render_page(
                    count=count,
                    result_html="예시 값을 채웠습니다. 계산하기를 눌러 확인하세요.",
                    values=values,
                    result_class="ok",
                )
            )
            return

        try:
            matrix = parse_matrix(form, count)
        except ValueError as exc:
            self._respond_html(render_page(count=count, result_html=f"입력 오류: {escape(str(exc))}"), status=HTTPStatus.BAD_REQUEST)
            return

        status, solution = solve_by_gauss_jordan(matrix)
        if status == "no_solution":
            result_html = "<strong>해가 없습니다.</strong><br/>입력한 식이 서로 모순됩니다."
            result_class = "err"
        elif status == "infinite":
            result_html = "<strong>해가 무한히 많습니다.</strong><br/>독립적인 식의 수가 미지수보다 적습니다."
            result_class = "warn"
        else:
            lines = ["<strong>유일한 해를 찾았습니다.</strong>"]
            for index, value in enumerate(solution, start=1):
                lines.append(f"x{index} = {escape(format_decimal(value))}")
            result_html = "<br/>".join(lines)
            result_class = "ok"

        self._respond_html(render_page(count=count, result_html=result_html, result_class=result_class))

    def _respond_html(self, html: str, status: HTTPStatus = HTTPStatus.OK) -> None:
        data = html.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def run_server() -> None:
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "8000"))
    server = ThreadingHTTPServer((host, port), EquationRequestHandler)
    host, port = server.server_address
    url = f"http://{host}:{port}/"

    print(f"연립방정식 계산기 실행 중: {url}")
    if host in {"127.0.0.1", "localhost"}:
        try:
            webbrowser.open(url, new=1, autoraise=True)
        except Exception:
            pass

    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        thread.join()
    except KeyboardInterrupt:
        server.shutdown()
        server.server_close()


def main() -> None:
    run_server()


if __name__ == "__main__":
    main()