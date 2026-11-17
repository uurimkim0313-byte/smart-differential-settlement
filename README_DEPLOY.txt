스마트 차등 정산기 - 공개 배포용

이 버전은 어제 제작한 정산 기능과 화면을 유지하면서 Render 등 외부 호스팅에서 접속할 수 있도록 서버 주소와 포트 설정을 수정한 버전입니다.

GitHub 저장소 최상위에 app.py, requirements.txt, templates/index.html이 있어야 합니다.
Render 설정: Build Command = pip install -r requirements.txt / Start Command = python app.py

로컬 실행은 Windows에서 run.bat 대신 python app.py로 실행할 수 있습니다. 기본 포트는 8000입니다.
