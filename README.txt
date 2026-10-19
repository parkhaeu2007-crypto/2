NEST 휴대폰 웹앱 배포

이 폴더는 HTTPS 웹 배포를 지원합니다. 배포 후 휴대폰에서 웹 주소를 열면 반응형 화면으로 쓸 수 있고, 브라우저 메뉴에서 홈 화면에 추가하면 앱 아이콘으로 실행할 수 있습니다. YouTube 자막과 공개 웹페이지/PDF 본문 가져오기는 배포된 서버리스 API를 사용합니다.

현재 배포 주소: https://nest-website-jet.vercel.app

기기 간 자료 동기화 설정
현재 배포본에는 동기화 기능이 포함되지 않았습니다. 이 폴더의 최신 파일을 Vercel에 다시 배포하고, 개인 Supabase 프로젝트를 한 번 연결해야 합니다.

1. supabase.com에서 프로젝트를 만듭니다.
2. Supabase 프로젝트의 SQL Editor를 열고 cloud_schema.sql의 전체 내용을 붙여넣어 실행합니다. 이 테이블은 계정마다 자료를 분리하며 RLS 정책으로 로그인한 사용자 본인 데이터만 허용합니다.
3. Supabase Project Settings → API Keys에서 Project URL과 Publishable key(구 anon public key)를 복사합니다. `service_role` 또는 `secret` 키는 절대 웹앱에 입력하지 마세요.
4. Supabase Authentication URL Configuration에서 Site URL과 Redirect URLs에 https://nest-website-jet.vercel.app 을 등록합니다.
5. NEST를 최신 파일로 다시 배포한 후 ☁ 버튼을 누르고 URL/Publishable key를 입력합니다. 새 계정을 만들거나 기존 계정으로 로그인합니다. 휴대폰에서도 같은 프로젝트 URL, 키, 계정을 입력하면 자료가 동기화됩니다.

처음 로그인할 때는 현재 브라우저에 있던 자료를 클라우드로 올립니다. 다른 기기의 자료도 합쳐져 저장됩니다. 자료 삭제와 대화 초기화도 다른 기기에 반영됩니다.

배포 방법 (Vercel + GitHub)
1. 이 nest-website 폴더 안의 파일을 GitHub 저장소의 최상위에 올립니다. 기존 앱 저장소를 사용한다면 index.html, api 폴더, manifest.webmanifest, sw.js, icon.svg, requirements.txt를 함께 반영합니다.
2. vercel.com에서 GitHub로 로그인하고 Add New → Project를 선택합니다.
3. 해당 저장소를 Import합니다. Root Directory가 이 앱 폴더인지 확인한 다음 Deploy를 누릅니다. 별도 빌드 명령은 필요 없습니다.
4. 배포가 끝나면 표시된 https://…vercel.app 주소를 휴대폰에서 엽니다.
5. iPhone은 Safari의 공유 메뉴 → 홈 화면에 추가, Android는 Chrome 메뉴 → 앱 설치 또는 홈 화면에 추가를 선택합니다.

사용 시 알아둘 점
- 자료는 현재 브라우저의 기기에 저장됩니다. PC에서 넣은 자료가 휴대폰에 자동으로 나타나지는 않습니다. 양쪽에서 같은 자료를 쓰려면 자료 동기화 기능과 계정/클라우드 데이터베이스를 별도로 연결해야 합니다.
- Ollama는 PC에서 직접 실행하는 로컬 AI라 휴대폰에서 PC의 Ollama에 자동 연결되지 않습니다. 휴대폰에서는 기본 학습 기능을 쓰고, Ollama 연결 설정은 해당 PC에서 사용하세요.
- PDF/사진 글자 인식 기능은 인터넷 연결이 필요합니다. 앱 화면은 한 번 연 뒤 일부 내용을 오프라인에서도 열 수 있지만 자막 수집은 인터넷 연결이 필요합니다.
- 공개 웹페이지 본문, 텍스트 PDF, YouTube 자막 링크를 자료로 가져올 수 있습니다. 로그인 전용 페이지, 스캔 PDF, 6MB가 넘는 파일, 사이트가 자동 수집을 막은 페이지는 지원하지 않을 수 있어요. 그런 자료는 파일을 직접 올리거나 텍스트를 붙여넣으세요.
- YouTube가 자막을 제공하지 않거나 요청을 제한한 영상은 가져오지 못할 수 있습니다. 영상 파일을 내려받지는 않습니다.
- Vercel의 기본 서버리스 실행량/요금 정책은 계정과 시점에 따라 다를 수 있습니다.

PC에서 기존 로컬 방식으로 쓸 때
Start-NEST.bat을 실행하면 로컬 서버로 앱과 자막 가져오기를 사용할 수 있습니다. 열린 검은 창을 앱을 쓰는 동안 유지하세요. Vercel 배포와 별도로 이 로컬 실행 방법도 계속 사용할 수 있습니다.
