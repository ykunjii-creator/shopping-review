## Telegram 알림 설정 방법

본 프로젝트는 결함 의심 리뷰가 감지되었을 때 Telegram Bot API를 이용해 알림 메시지를 전송합니다.
보안을 위해 실제 Bot Token과 Chat ID는 GitHub에 포함하지 않았으며, 로컬 실행 시 사용자가 직접 입력해야 합니다.

### 1. Telegram Bot 생성하기

1. Telegram에서 `BotFather`를 검색합니다.
2. BotFather 채팅방에서 아래 명령어를 입력합니다.

```text
/newbot
```

3. 봇 이름을 입력합니다.

```text
Review Alert Bot
```

4. 봇 username을 입력합니다.
   username은 반드시 `bot`으로 끝나야 합니다.

```text
review_alert_sample_bot
```

5. BotFather가 봇 생성을 완료하면 `HTTP API:` 항목을 제공합니다.

예시:

```text
HTTP API: 1234567890:ABCdefGHI-jkl1MNO2p3qrST4Uvwxyz5
```

이 값이 프로젝트에서 사용하는 `<토큰>`에 해당합니다.

이때 `HTTP API:` 뒤에 있는 전체 문자열이 Bot Token입니다.

`1234567890:ABCdefGHI-jkl1MNO2p3qrST4Uvwxyz5`

해당 값을 Telegram 요청 URL의 `<토큰>` 위치에 입력합니다.


> 주의: Bot Token은 비밀번호와 같은 민감 정보이므로 GitHub에 그대로 업로드하지 않습니다.

---

### 2. Chat ID 확인하기

1. 생성한 Telegram 봇 채팅방에 들어갑니다.
2. 아무 메시지나 보냅니다.

```text
hi
```

3. 브라우저 주소창에 아래 형식의 URL을 입력합니다.

```text
https://api.telegram.org/bot<토큰>/getUpdates
```

예시:

```text
https://api.telegram.org/bot1234567890:ABCdefGHI-jkl1MNO2p3qrST4Uvwxyz5/getUpdates
```

4. 응답 결과에서 아래와 같은 부분을 찾습니다.

```json
"chat": {
  "id": 123456789
}
```

여기서 `123456789`가 `<나의chatid>`에 해당합니다.

만약 결과가 아래처럼 비어 있다면, 봇에게 먼저 메시지를 보낸 뒤 페이지를 새로고침합니다.

```json
{
  "ok": true,
  "result": []
}
```

---

### 3. UiPath에 Telegram URL 입력하기

UiPath의 `Send_Telegram_Message.xaml` 파일에서 HTTP Request의 Endpoint URL을 아래 형식으로 설정합니다.

```text
https://api.telegram.org/bot<토큰>/sendMessage?chat_id=<나의chatid>&text=[결함 리뷰 알림]%0A결함 의심 리뷰가 감지되었습니다.%0A메일 확인이 필요합니다.
```

`<토큰>`에는 BotFather에서 발급받은 Bot Token을 입력합니다.
`<나의chatid>`에는 `getUpdates` 응답에서 확인한 Chat ID를 입력합니다.

예시 형식:

```text
https://api.telegram.org/bot1234567890:ABCdefGHI-jkl1MNO2p3qrST4Uvwxyz5/sendMessage?chat_id=123456789&text=[결함 리뷰 알림]%0A결함 의심 리뷰가 감지되었습니다.%0A메일 확인이 필요합니다.
```

---

### 4. 테스트 방법

브라우저 주소창에 `sendMessage` URL을 직접 입력했을 때 Telegram으로 메시지가 오면 정상 연결된 것입니다.

또는 UiPath에서 `Send_Telegram_Message.xaml`을 단독 실행하여 테스트할 수 있습니다.

정상 동작 시 Telegram으로 아래와 같은 메시지가 전송됩니다.

```text
[결함 리뷰 알림]
결함 의심 리뷰가 감지되었습니다.
확인이 필요합니다.
```

---

### 5. 보안 주의사항

* 실제 Bot Token은 GitHub에 업로드하지 않습니다.
* 실제 Chat ID도 공개 저장소에 그대로 노출하지 않는 것을 권장합니다.
* GitHub에는 아래처럼 placeholder 형태로 작성합니다.

```text
https://api.telegram.org/bot<토큰>/sendMessage?chat_id=<나의chatid>&text=...
```

로컬 테스트 시에만 `<토큰>`과 `<나의chatid>`를 실제 값으로 교체하여 실행합니다.
