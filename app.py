from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse
import json
import os
from pathlib import Path

ROOT = Path(__file__).parent
# Render supplies PORT. 0.0.0.0 allows access from outside the container.
HOST = "0.0.0.0"
PORT = int(os.environ.get("PORT", "8000"))

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if urlparse(self.path).path == "/api/health":
            body = json.dumps({"ok": True}, ensure_ascii=False).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if urlparse(self.path).path not in ("/", "/index.html"):
            self.send_error(404)
            return
        body = (ROOT / "templates" / "index.html").read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        if urlparse(self.path).path != "/api/settle":
            self.send_error(404)
            return
        try:
            size = int(self.headers.get("Content-Length", "0"))
            data = json.loads(self.rfile.read(size).decode("utf-8"))
            result = calculate(data)
            self.reply(200, {"ok": True, "result": result})
        except (ValueError, TypeError, KeyError) as e:
            self.reply(400, {"ok": False, "error": str(e)})
        except Exception:
            self.reply(500, {"ok": False, "error": "정산 중 오류가 발생했습니다."})

    def reply(self, status, payload):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

def calculate(data):
    total = int(data["total"])
    names = [x.strip() for x in data["people"] if x.strip()]
    if total < 0:
        raise ValueError("총 금액은 0원 이상이어야 합니다.")
    if not names:
        raise ValueError("참여자를 한 명 이상 입력해 주세요.")
    if len(set(names)) != len(names):
        raise ValueError("참여자 이름은 중복될 수 없습니다.")

    excluded_reasons = {}
    excluded = set()
    for item in data.get("excluded", []):
        if isinstance(item, dict):
            name = item.get("name", "").strip()
            reason = item.get("reason", "").strip()
        else:
            name, reason = str(item).strip(), ""
        if name:
            excluded.add(name)
            excluded_reasons[name] = reason
    unknown = excluded.difference(names)
    if unknown:
        raise ValueError("제외 대상은 참여자 이름 중에서 선택해 주세요.")
    fixed = {}
    for item in data.get("fixed", []):
        name = item.get("name", "").strip()
        amount = int(item.get("amount", 0))
        if name not in names:
            raise ValueError(f"'{name}'은(는) 참여자 목록에 없습니다.")
        if name in excluded:
            raise ValueError(f"제외된 사람({name})에게 고정 금액을 지정할 수 없습니다.")
        if amount < 0:
            raise ValueError("개별 지정 금액은 0원 이상이어야 합니다.")
        if name in fixed:
            raise ValueError(f"{name}의 개별 지정 금액이 중복되었습니다.")
        fixed[name] = amount

    fixed_reasons = {item.get("name", "").strip(): item.get("reason", "").strip()
                     for item in data.get("fixed", [])}
    fixed_sum = sum(fixed.values())
    if fixed_sum > total:
        raise ValueError("개별 지정 금액의 합이 총 금액보다 큽니다.")
    remaining_people = [n for n in names if n not in excluded and n not in fixed]
    remaining = total - fixed_sum
    if not remaining_people and remaining != 0:
        raise ValueError("남은 금액을 나눌 참여자가 없습니다. 개별 지정 금액을 확인해 주세요.")
    shares = {n: 0 for n in names}
    shares.update(fixed)
    if remaining_people:
        q, r = divmod(remaining, len(remaining_people))
        for i, name in enumerate(remaining_people):
            shares[name] = q + (1 if i < r else 0)
    return {
        "total": total,
        "people_count": len(names),
        "shares": [{"name": n, "amount": shares[n]} for n in names],
        "check_sum": sum(shares.values()),
        "excluded": [{"name": n, "reason": excluded_reasons.get(n, "")} for n in names if n in excluded],
        "fixed": [{"name": n, "amount": amount, "reason": fixed_reasons.get(n, "")}
                  for n, amount in fixed.items()]
    }

if __name__ == "__main__":
    print(f"스마트 차등 정산기가 실행되었습니다: http://{HOST}:{PORT}")
    HTTPServer((HOST, PORT), Handler).serve_forever()
