<div align="center">
  <img width="600" alt="Coding Agent Telegram" src="https://github.com/user-attachments/assets/aca106f8-0d64-40e9-94d9-2542da5dfde9" />
  <h1>Coding Agent Telegram 🚀</h1>
  <p>
    <a href="https://github.com/daocha/coding-agent-telegram/blob/main/README.md">English</a> |
    <a href="https://github.com/daocha/coding-agent-telegram/blob/main/README.de.md">Deutsch</a> |
    <a href="https://github.com/daocha/coding-agent-telegram/blob/main/README.fr.md">Français</a> |
    <a href="https://github.com/daocha/coding-agent-telegram/blob/main/README.ja.md">日本語</a> |
    <a href="https://github.com/daocha/coding-agent-telegram/blob/main/README.ko.md">한국어</a> |
    <a href="https://github.com/daocha/coding-agent-telegram/blob/main/README.nl.md">Nederlands</a> |
    <a href="https://github.com/daocha/coding-agent-telegram/blob/main/README.th.md">ไทย</a> |
    <a href="https://github.com/daocha/coding-agent-telegram/blob/main/README.vi.md">Tiếng Việt</a> |
    <a href="https://github.com/daocha/coding-agent-telegram/blob/main/README.zh-CN.md">简体中文</a> |
    <a href="https://github.com/daocha/coding-agent-telegram/blob/main/README.zh-HK.md">繁體中文（香港）</a> |
    <a href="https://github.com/daocha/coding-agent-telegram/blob/main/README.zh-TW.md">繁體中文（台灣）</a>
  </p>
  <p><strong>เบา รองรับหลายบอต หลายเซสชัน หลายงาน พร้อม AI Coding Agent ทำงานได้ 24/7</strong></p>
  <p>ควบคุม AI Coding Agent ที่รันในเครื่องของคุณจากที่ไหนก็ได้ผ่าน Telegram</p>
  <p>
    <img src="https://img.shields.io/badge/stability-experimental-orange.svg" alt="Experimental" />
    <a href="https://opensource.org/licenses/MIT">
      <img src="https://img.shields.io/badge/License-MIT-blue.svg" alt="MIT License" />
    </a>
    <a href="http://github.com/daocha/coding-agent-telegram/releases/latest">
      <img src="https://img.shields.io/github/v/release/daocha/coding-agent-telegram?label=Latest&color=green" alt="Latest Release" />
    </a>
    <img src="https://img.shields.io/badge/python-3.9+-blue" alt="Python 3.9+" />
  </p>
</div>

<table border="0">
   <tr>
   <td border="0">

   ## ✨ ทำไมถึงควรใช้
  - ✅ เบา: ไม่ต้องใช้เฟรมเวิร์กหนัก ๆ และตรวจสอบการทำงานได้ง่าย
  - ✅ หลายบอต: รองรับหลายแชต หลายเซสชัน
  - ✅ ใช้ Telegram เพื่อควบคุม Codex / Copilot CLI
  - ✅ ตรวจคำตอบและไฟล์ที่ถูกแก้ได้ง่ายใน code block
  - ✅ ส่งคำถามต่อคิวไว้ได้ระหว่างที่ agent กำลังทำงาน
  - ✅ รองรับ ✏️ ข้อความ, 🌄 รูปภาพ และ 🎙️ ข้อความเสียง

   ## 🔁 สลับอุปกรณ์และเซสชันได้ลื่นไหล

  เริ่มเซสชันจาก Telegram แล้วค่อยกลับไปทำต่อบนคอมพิวเตอร์ด้วยเซสชัน Codex/Copilot CLI เดิมได้ทันที และใช้ `/switch` เพื่อสลับกลับไปมาระหว่าง Telegram กับ command line ได้อย่างง่ายดาย
  
  - ใช้ `/switch` เพื่อทำงานต่อจากเซสชันในเครื่อง
  - รองรับเซสชันย้อนหลัง

   ## 🛠️ ตัวอย่าง flow การใช้งานบนเครื่อง
   ```bash
   coding-agent-telegram # หรือรัน ./startup.sh
   ```

   ##### ใน Telegram:

   ```text
   /project my-project
   /new
   Fix the failing API test in the current project
   ```

   </td>
   <td width="350" border="0">
   <img src="https://github.com/user-attachments/assets/cecb6de6-ecf0-4bf4-af70-b98071c68885" />
   </td>
   </tr>
</table>

→ ติดตั้งด้วยคำสั่งบรรทัดเดียว: 
```
curl -fsSL https://raw.githubusercontent.com/daocha/coding-agent-telegram/main/install.sh | bash
```

<table>
   <tr>
   <td width="65%" valign="top">

   ## 🔐 ความปลอดภัย

- กำหนด whitelist สำหรับแชตส่วนตัวด้วย `ALLOWED_CHAT_IDS`
- อนุญาตให้มี agent ที่ทำงานอยู่ได้เพียงหนึ่งตัวต่อหนึ่ง project เพื่อลดการเขียนทับกัน
- ซ่อน diff ของไฟล์ที่มีข้อมูลอ่อนไหว
- ปิดบัง API keys, tokens, ค่าใน `.env`, certificates, SSH keys และข้อมูลลักษณะใกล้เคียงกับความลับก่อนส่งกลับไปที่ Telegram
- ข้อมูล runtime ของแอปเก็บไว้ใต้ `~/.coding-agent-telegram`
- โฟลเดอร์ที่มีอยู่เดิมอาจต้องยืนยัน trust ก่อนทำ Git operation ที่มีการแก้ไข
- เซิร์ฟเวอร์ไม่มีการเรียกใช้งานภายนอกแบบซ่อน ทุกอย่างยังอยู่ในการควบคุมของคุณ
- ทำงานร่วมกับ Codex Sandbox mode ได้ดี โดยไม่ต้องให้สิทธิ์ `danger-full-access`
   </td>
   <td width="35%" valign="top">

   ## ✅ สิ่งที่ต้องมี

ก่อนเริ่มเซิร์ฟเวอร์ โปรดเตรียม:

- Python 3.9 ขึ้นไป
- Telegram bot token จาก _@BotFather_
- Telegram chat ID ของคุณ
- ติดตั้ง Codex CLI และ/หรือ Copilot CLI ไว้ในเครื่องแล้ว
- [ติดตั้ง Codex CLI](https://developers.openai.com/codex/cli)
- [ติดตั้ง Copilot CLI](https://github.com/features/copilot/cli)
- [ทางเลือก] Whisper, ffmpeg
   </td>
   </tr>
</table>

## 🦞 ถ้ามี Openclaw อยู่แล้ว ทำไมยังต้องใช้ตัวนี้?
Openclaw มีความสามารถครบมาก และมี agent loop แบบรวมมาให้แล้วชื่อ Pi-Agent เหมาะกับ use case ที่หลากหลายกว่า ผมเองก็ชอบ Openclaw และเคยใช้มันเขียนโค้ดเหมือนกัน แต่สำหรับ coding โดยตรง มันไม่ใช่ตัวเลือกที่ดีที่สุดเสมอไป เพราะมี system prompt ขนาดใหญ่และ context ที่ติดมาด้วยมากกว่า Claude Code / Codex / Copilot จึงมักทำงานด้าน coding ได้มีประสิทธิภาพกว่า แม่นยำกว่า ตรงประเด็นกว่า และเสียสมาธิน้อยกว่า โปรเจ็กต์นี้ตั้งใจให้เรียบง่ายมาก โดยเชื่อมต่อกับ Codex / Copilot CLI เท่านั้น ดังนั้นคุณจึงมอบหมายงานให้ Codex / Copilot ทำได้โดยตรง

## 🚀 เริ่มต้นอย่างรวดเร็ว

### วิธีที่ A: สคริปต์ bootstrap แบบบรรทัดเดียว
```bash
curl -fsSL https://raw.githubusercontent.com/daocha/coding-agent-telegram/main/install.sh | bash
```

### วิธีที่ B: ติดตั้งจาก PyPI ด้วย `pip`
```bash
pip install coding-agent-telegram
coding-agent-telegram
```

### วิธีที่ C: รันจาก repository ที่ clone มา
```bash
git clone https://github.com/daocha/coding-agent-telegram
cd coding-agent-telegram
./startup.sh
```

### 🌐 เริ่ม Bot Server
##### ครั้งแรกแอปจะสร้างไฟล์ env และบอกว่าต้องกรอกค่าใดบ้าง
##### หลังแก้ไฟล์ env แล้ว ให้รันอีกครั้ง:
```bash
# หากคุณทำตามวิธีที่ A หรือ วิธีที่ B ให้รัน
coding-agent-telegram

# หากคุณทำตามวิธีที่ C ให้รันสิ่งนี้อีกครั้ง
./startup.sh
```

## 🎙️ [ทางเลือก] ฟีเจอร์เสียงเป็นข้อความ: เตรียมส่วนที่ OpenAI-Whisper ต้องใช้ในเครื่อง

ส่วนนี้ใช้เปิดการแปลงข้อความจากข้อความเสียง Telegram ด้วย Whisper แบบโลคัลตามตัวเลือกของคุณ ไฟล์เสียงถูกจำกัดไว้ที่สูงสุด `20 MB`

```bash
# ถ้าติดตั้งด้วย pip
coding-agent-telegram-stt-install

# ถ้าใช้งานจาก repository ที่ clone มา
./install-stt.sh
```

ค่า env ที่แนะนำ:

```text
ENABLE_OPENAI_WHISPER_SPEECH_TO_TEXT=true
OPENAI_WHISPER_MODEL=base
OPENAI_WHISPER_TIMEOUT_SECONDS=120
```

หมายเหตุ:

- Whisper จะดาวน์โหลดโมเดลที่เลือกโดยอัตโนมัติครั้งแรกไปยัง `~/.cache/whisper`
- หากเลือก `OPENAI_WHISPER_MODEL=turbo` การถอดข้อความจากเสียงครั้งแรกมีโอกาสหมดเวลามากขึ้น ขณะ `large-v3-turbo.pt` ยังดาวน์โหลดไม่เสร็จ
- หลังจากถอดข้อความจากเสียงแล้ว บอตจะส่งข้อความที่รู้จำได้กลับไปใน Telegram ก่อน แล้วจึงส่งต่อให้เอเจนต์ เพื่อช่วยตรวจสอบความคลาดเคลื่อนของการรู้จำ

## 🔑 ตั้งค่า Telegram

### รับ Bot Token

1. เปิด Telegram และเริ่มแชตกับ `@BotFather`
2. ส่ง `/newbot`
3. ทำตามขั้นตอนเพื่อกำหนด:
   - ชื่อที่แสดง
   - ชื่อผู้ใช้ bot ที่ลงท้ายด้วย `bot`
4. BotFather จะส่ง HTTP API token กลับมา
5. นำ token นี้ไปใส่ใน `TELEGRAM_BOT_TOKENS` ภายใน `~/.coding-agent-telegram/.env_coding_agent_telegram`

### รับ Chat ID

วิธีที่เชื่อถือได้ที่สุดคือใช้ Telegram `getUpdates` API พร้อม bot token ของคุณเอง

1. เริ่มแชตกับบอตของคุณแล้วส่งข้อความ เช่น `/start`
2. เปิด URL นี้ในเบราว์เซอร์ โดยแทนที่ `<BOT_TOKEN>`:

```text
https://api.telegram.org/bot<BOT_TOKEN>/getUpdates
```

3. หา object `chat` ใน JSON response
4. คัดลอกค่า `id` ที่เป็นตัวเลข
5. นำค่านี้ไปใส่ใน `ALLOWED_CHAT_IDS` ภายใน `~/.coding-agent-telegram/.env_coding_agent_telegram`

หมายเหตุ:

- สำหรับแชตส่วนตัว chat ID มักเป็นจำนวนเต็มบวก
- หาก `getUpdates` คืนค่ากลับมาเป็นค่าว่าง ให้ส่งข้อความหาบอตอีกครั้งแล้วลองใหม่

## 📨 ประเภทข้อความที่รองรับ

บอตรองรับสิ่งต่อไปนี้ในตอนนี้:

- ข้อความตัวอักษร
- รูปภาพ
- ข้อความเสียงและไฟล์เสียง เมื่อกำหนด `ENABLE_OPENAI_WHISPER_SPEECH_TO_TEXT=true` และติดตั้งส่วนที่ Whisper ต้องใช้ในเครื่องแล้ว
- ปัจจุบัน Codex และ Copilot รองรับเฉพาะข้อความและรูปภาพ ยังไม่รองรับวิดีโอ

## 🤖 คำสั่ง Telegram

<table>
  <tr>
    <td width="332"><code>/ผู้ให้บริการ</code></td>
    <td>เลือกผู้ให้บริการสำหรับเซสชันใหม่ โดยค่าที่เลือกจะถูกเก็บแยกตาม bot และ chat จนกว่าคุณจะเปลี่ยน</td>
  </tr>
  <tr>
    <td width="332"><code>/project &lt;project_folder&gt;</code></td>
    <td>ตั้งค่าโฟลเดอร์ project ปัจจุบัน หากโฟลเดอร์ยังไม่มี แอปจะสร้างและทำเครื่องหมายว่า trusted หากมีอยู่แล้วแต่ยัง untrusted แอปจะถามยืนยัน trust ก่อน</td>
  </tr>
  <tr>
    <td width="332"><code>/branch &lt;new_branch&gt;</code></td>
    <td>เตรียมหรือสลับ branch สำหรับ project ปัจจุบัน หาก branch มีอยู่แล้ว บอตจะถือ branch นั้นเป็น source candidate หากยังไม่มี บอตจะใช้ default branch ของ repository เป็น source candidate</td>
  </tr>
  <tr>
    <td width="332"><code>/branch &lt;origin_branch&gt; &lt;new_branch&gt;</code></td>
    <td>เตรียมหรือสลับ branch โดยใช้ <code>&lt;origin_branch&gt;</code> เป็น source candidate สำหรับทั้งสองรูปแบบ บอตจะแสดงเฉพาะ source choices ที่มีอยู่จริงเท่านั้น: <code>local/&lt;branch&gt;</code> และ <code>origin/&lt;branch&gt;</code> หากมีเพียงตัวเดียวก็จะแสดงเพียงตัวนั้น หากไม่มีเลย บอตจะแจ้งว่าไม่พบ branch source</td>
  </tr>
  <tr>
    <td width="332"><code>/current</code></td>
    <td>แสดง เซสชันที่ใช้งานอยู่ ของ bot และ chat ปัจจุบัน</td>
  </tr>
  <tr>
    <td width="332"><code>/new [session_name]</code></td>
    <td>สร้างเซสชันใหม่สำหรับ project ปัจจุบัน หากไม่ระบุชื่อ บอตจะใช้รหัสเซสชันจริง หากยังไม่มีผู้ให้บริการ, project หรือ branch บอตจะพาคุณไปยังขั้นตอนที่ขาดอยู่</td>
  </tr>
  <tr>
    <td width="332"><code>/switch</code></td>
    <td>แสดงเซสชันล่าสุด โดยเรียงจากใหม่ไปเก่า รายการนี้รวมทั้งเซสชันที่ bot ดูแลและ local Codex/Copilot CLI เซสชันของ project ปัจจุบัน</td>
  </tr>
  <tr>
    <td width="332"><code>/switch page &lt;number&gt;</code></td>
    <td>แสดงหน้าถัดไปของเซสชันที่จัดเก็บไว้</td>
  </tr>
  <tr>
    <td width="332"><code>/switch &lt;session_id&gt;</code></td>
    <td>สลับไปยังเซสชันที่ระบุด้วย ID หากเลือก local CLI เซสชัน บอตจะ import เข้าสู่ state แล้วทำงานต่อจากตรงนั้น</td>
  </tr>
  <tr>
    <td width="332"><code>/compact</code></td>
    <td>สร้างเซสชันแบบย่อใหม่จากเซสชันที่กำลังใช้งาน แล้วสลับไปที่เซสชันนั้น</td>
  </tr>
  <tr>
    <td width="332"><code>/commit &lt;git commands&gt;</code></td>
    <td>รันคำสั่งที่เกี่ยวข้องกับ <code>git commit</code> ซึ่งผ่านการตรวจสอบแล้วภายใน project ของ เซสชันที่ใช้งานอยู่ ใช้ได้เมื่อ <code>ENABLE_COMMIT_COMMAND=true</code> เท่านั้น คำสั่ง Git ที่มีการแก้ไขต้องใช้ project ที่ trusted</td>
  </tr>
  <tr>
    <td width="332"><code>/push</code></td>
    <td>push <code>origin &lt;branch&gt;</code> สำหรับ เซสชันที่ใช้งานอยู่ ปัจจุบัน โดยบอตจะขอการยืนยันก่อน push</td>
  </tr>
  <tr>
    <td width="332"><code>/abort</code></td>
    <td>ยกเลิก การรันของเอเจนต์ ปัจจุบันของ project นี้ หากมี คำถามที่เข้าคิว รออยู่ บอตจะถามว่าจะให้ประมวลผลต่อหรือไม่</td>
  </tr>
</table>

<h2>⚙️ ตัวแปรสภาพแวดล้อม</h2>

<h3>ตำแหน่งไฟล์ env หลัก:</h3>

<table>
  <tr>
    <td><code>CODING_AGENT_TELEGRAM_ENV_FILE</code></td>
    <td>ใช้สิ่งนี้หากต้องการให้แอปชี้ไปยังไฟล์ env ที่กำหนดเอง</td>
  </tr>
  <tr>
    <td><code>~/.coding-agent-telegram/.env_coding_agent_telegram</code></td>
    <td>ตำแหน่งไฟล์ env เริ่มต้น</td>
  </tr>
  <tr>
    <td><code>./.env_coding_agent_telegram</code></td>
    <td>จะใช้ก็ต่อเมื่อไฟล์ local นี้มีอยู่แล้วเท่านั้น</td>
  </tr>
</table>

<h3>จำเป็น</h3>

<table>
  <tr>
    <td width="332"><code>WORKSPACE_ROOT</code></td>
    <td>โฟลเดอร์หลักที่เก็บโฟลเดอร์โปรเจกต์ของคุณ</td>
  </tr>
  <tr>
    <td width="332"><code>TELEGRAM_BOT_TOKENS</code></td>
    <td>Telegram bot tokens แบบคั่นด้วย comma</td>
  </tr>
  <tr>
    <td width="332"><code>ALLOWED_CHAT_IDS</code></td>
    <td>Telegram private chat IDs แบบคั่นด้วย comma ที่ได้รับอนุญาตให้ใช้บอต</td>
  </tr>
</table>

<h3>การตั้งค่าทั่วไป</h3>

<table>
  <tr>
    <td width="332"><code>APP_LOCALE</code></td>
    <td>ภาษา UI สำหรับข้อความของบอตและคำอธิบายคำสั่งที่ใช้ร่วมกัน ค่าที่รองรับ: <code>en</code>, <code>de</code>, <code>fr</code>, <code>ja</code>, <code>ko</code>, <code>nl</code>, <code>th</code>, <code>vi</code>, <code>zh-CN</code>, <code>zh-HK</code>, <code>zh-TW</code></td>
  </tr>
  <tr>
    <td width="332"><code>CODEX_BIN</code></td>
    <td>คำสั่งที่ใช้เรียก Codex CLI ค่าเริ่มต้น: <code>codex</code></td>
  </tr>
  <tr>
    <td width="332"><code>COPILOT_BIN</code></td>
    <td>คำสั่งที่ใช้เรียก Copilot CLI ค่าเริ่มต้น: <code>copilot</code></td>
  </tr>
  <tr>
    <td width="332"><code>CODEX_MODEL</code></td>
    <td>กำหนด model ของ Codex เพิ่มเติมได้แบบ optional หากปล่อยว่างจะใช้ model เริ่มต้นของ Codex CLI ตัวอย่าง: <code>gpt-5.4</code> <a href="https://developers.openai.com/codex/models" target="_blank">OpenAI Codex/OpenAI models</a></td>
  </tr>
  <tr>
    <td width="332"><code>COPILOT_MODEL</code></td>
    <td>กำหนด model ของ Copilot เพิ่มเติมได้แบบ optional หากปล่อยว่างจะใช้ model เริ่มต้นของ Copilot CLI ตัวอย่าง: <code>gpt-5.4</code>, <code>claude-sonnet-4.6</code> <a href="https://docs.github.com/en/copilot/reference/ai-models/supported-models" target="_blank">GitHub Copilot supported models</a></td>
  </tr>
  <tr>
    <td width="332"><code>CODEX_APPROVAL_POLICY</code></td>
    <td>โหมด approval ที่ส่งให้ Codex ค่าเริ่มต้น: <code>never</code></td>
  </tr>
  <tr>
    <td width="332"><code>CODEX_SANDBOX_MODE</code></td>
    <td>โหมด sandbox ที่ส่งให้ Codex ค่าเริ่มต้น: <code>workspace-write</code></td>
  </tr>
  <tr>
    <td width="332"><code>CODEX_SKIP_GIT_REPO_CHECK</code></td>
    <td>หากเปิดไว้ จะข้ามการตรวจ trusted-repo ของ Codex เสมอ</td>
  </tr>
  <tr>
    <td width="332"><code>ENABLE_COMMIT_COMMAND</code></td>
    <td>เปิดใช้งานคำสั่ง Telegram <code>/commit</code> ค่าเริ่มต้น: <code>false</code></td>
  </tr>
  <tr>
    <td width="332"><code>AGENT_HARD_TIMEOUT_SECONDS</code></td>
    <td>ฮาร์ดไทม์เอาต์สำหรับ การรันของเอเจนต์ หนึ่งครั้ง ค่าเริ่มต้น: <code>0</code> (ปิดใช้งาน)</td>
  </tr>
  <tr>
    <td width="332"><code>SNAPSHOT_TEXT_FILE_MAX_BYTES</code></td>
    <td>ขนาดไฟล์สูงสุดที่บอตจะอ่านเป็นข้อความเพื่อสร้าง สแนปช็อตก่อนและหลังการรัน สำหรับ diff ของแต่ละ run ค่าเริ่มต้น: <code>200000</code></td>
  </tr>
  <tr>
    <td width="332"><code>MAX_TELEGRAM_MESSAGE_LENGTH</code></td>
    <td>ขนาดข้อความสูงสุดก่อนที่แอปจะแบ่งการตอบกลับ ค่าเริ่มต้น: <code>3000</code></td>
  </tr>
  <tr>
    <td width="332"><code>ENABLE_SENSITIVE_DIFF_FILTER</code></td>
    <td>ซ่อน diff สำหรับไฟล์ที่มีข้อมูลอ่อนไหว ค่าเริ่มต้น: <code>true</code></td>
  </tr>
  <tr>
    <td width="332"><code>ENABLE_SECRET_SCRUB_FILTER</code></td>
    <td>ปิดบัง tokens, keys, ค่า <code>.env</code>, certificates และข้อมูลลักษณะคล้ายความลับก่อนส่งไปยัง Telegram ค่าเริ่มต้น: <code>true</code> (แนะนำอย่างยิ่ง)</td>
  </tr>
  <tr>
    <td width="332"><code>SNAPSHOT_INCLUDE_PATH_GLOBS</code></td>
    <td>บังคับรวม path ที่ตรงเงื่อนไขเข้าใน diff ตัวอย่าง: <code>.github/*,.profile.test,.profile.prod</code></td>
  </tr>
  <tr>
    <td width="332"><code>SNAPSHOT_EXCLUDE_PATH_GLOBS</code></td>
    <td>เพิ่มกฎยกเว้น diff เพิ่มเติมทับบนค่าเริ่มต้นของแพ็กเกจ ตัวอย่าง: <code>.*,personal/*,sensitive*.txt</code> หมายเหตุ: <code>.*</code> จะตรงกับ path ที่ซ่อนอยู่ รวมถึงไฟล์ใน ไดเรกทอรีที่ซ่อนอยู่</td>
  </tr>
</table>








<h3>เสียงเป็นข้อความ</h3>

<table>
  <tr>
    <td width="332"><code>ENABLE_OPENAI_WHISPER_SPEECH_TO_TEXT</code></td>
    <td>ค่าเริ่มต้น: <code>false</code> หากเป็น <code>true</code> จะเปิดใช้การรู้จำข้อความเสียงและไฟล์เสียง ระบบจะตรวจสอบไบนารีหรือไลบรารีที่จำเป็น และแจ้งให้ผู้ใช้ติดตั้งหากยังขาดอยู่</td>
  </tr>
  <tr>
    <td><code>OPENAI_WHISPER_MODEL</code></td>
    <td>โมเดลสำหรับ Whisper STT ค่าเริ่มต้น: <code>base</code><br />โมเดลที่ใช้ได้: <code>tiny</code> ประมาณ <code>72 MB</code>, <code>base</code> ประมาณ <code>139 MB</code>, <code>large-v3-turbo</code> ประมาณ <code>1.5 GB</code><br />โมเดลจะถูกดาวน์โหลดอัตโนมัติเมื่อคุณส่งข้อความเสียงครั้งแรก แนะนำให้ใช้ <code>base</code> สำหรับการใช้งานทั่วไป หากต้องการความแม่นยำและคุณภาพที่ดีขึ้นสามารถลอง <code>turbo</code> ได้</td>
  </tr>
  <tr>
    <td><code>OPENAI_WHISPER_TIMEOUT_SECONDS</code></td>
    <td>ค่าเริ่มต้น: <code>120</code> ระยะหมดเวลาของกระบวนการ STT โดยทั่วไปการประมวลผลเร็วพออยู่แล้ว แต่หากเลือก <code>turbo</code> การส่งข้อความเสียงครั้งแรกอาจใช้เวลานานเกินกำหนดระหว่างดาวน์โหลดโมเดล ขึ้นอยู่กับความเร็วอินเทอร์เน็ตของคุณ</td>
  </tr>
</table>

<h3>สถานะและบันทึก</h3>

<table>
  <tr>
    <td><code>~/.coding-agent-telegram/state.json</code></td>
    <td>ไฟล์สถานะเซสชันหลัก</td>
  </tr>
  <tr>
    <td><code>~/.coding-agent-telegram/state.json.bak</code></td>
    <td>ไฟล์สำรองของสถานะ</td>
  </tr>
  <tr>
    <td><code>~/.coding-agent-telegram/logs</code></td>
    <td>ไดเรกทอรีบันทึก</td>
  </tr>
</table>

ตัวอย่าง:

```env
APP_LOCALE=en
WORKSPACE_ROOT=~/git
TELEGRAM_BOT_TOKENS=bot_token_one
ALLOWED_CHAT_IDS=123456789
DEFAULT_AGENT_PROVIDER=codex
CODEX_BIN=codex
COPILOT_BIN=copilot
CODEX_APPROVAL_POLICY=never
CODEX_SANDBOX_MODE=workspace-write
ENABLE_SENSITIVE_DIFF_FILTER=true
ENABLE_SECRET_SCRUB_FILTER=true
```

## 🧠 การจัดการเซสชัน

เซสชันถูกแยกตาม:

- Telegram bot
- Telegram chat

ดังนั้นบัญชี Telegram เดียวกันสามารถใช้หลาย bot ได้โดยไม่ทำให้เซสชันปะปนกัน

ตัวอย่าง:

- Bot A + chat ของคุณ -> งาน backend
- Bot B + chat ของคุณ -> งาน frontend
- Bot C + chat ของคุณ -> งาน infra

เซสชันที่ใช้งานอยู่ ยังผูกกับสิ่งต่อไปนี้ด้วย:

- โฟลเดอร์โปรเจ็กต์
- ผู้ให้บริการ
- ชื่อ branch หากมี

<details>
<summary><b>แต่ละเซสชันจะเก็บข้อมูล:</b></summary>

- ชื่อเซสชัน
- โฟลเดอร์โปรเจ็กต์
- ชื่อ branch
- ผู้ให้บริการ
- timestamps
- การเลือก เซสชันที่ใช้งานอยู่ ภายใต้ขอบเขต bot/chat นั้น
</details>

### 🔓 ล็อกการทำงานพร้อมกันของเวิร์กสเปซ

จะมี การรันของเอเจนต์ ที่ active ได้พร้อมกันเพียงหนึ่งตัวต่อ **โฟลเดอร์โปรเจ็กต์** ไม่ว่า chat หรือ Telegram bot ตัวใดจะเป็นผู้เริ่มก็ตาม

- **โปรเจ็กต์กำลังถูกใช้งาน**: ใน workspace นั้นมี การรันของเอเจนต์ ทำงานอยู่แล้ว
- **เอเจนต์กำลังทำงานอยู่**: run ตัวนั้นยังประมวลผลคำขอปัจจุบันไม่เสร็จ

บอตบังคับกติกานี้เพื่อไม่ให้มีสอง agent เขียนลง workspace เดียวกันพร้อมกัน ช่วยลดการแก้ไขชนกันและลดโอกาสข้อมูลเสียหาย

หากมีข้อความเข้ามาในขณะที่ project เดียวกันกำลังมี agent ทำงานอยู่ บอตจะตอบทันทีว่า:

> ⏳ มี agent กำลังทำงานอยู่บน project นี้แล้ว โปรดรอให้เสร็จก่อน

lock นี้อยู่ในหน่วยความจำ ไม่ได้เก็บลงดิสก์ จึงถูกปล่อยอัตโนมัติเมื่อ agent ทำงานเสร็จ ล้มเหลว หรือ server รีสตาร์ต

### 💬 คำถามที่เข้าคิว

หาก project ปัจจุบันมี การรันของเอเจนต์ ทำงานอยู่แล้ว ข้อความตัวอักษรที่ส่งมาภายหลังจะไม่ถูกปฏิเสธ แต่จะถูกนำไปเข้าคิวแทน

- คำถามใหม่จะถูกต่อท้ายในไฟล์ queued-questions บนดิสก์
- agent ปัจจุบันยังคงทำงานกับคำขอเดิมต่อไป
- เมื่อ run นั้นจบแบบปกติ บอตจะเริ่มประมวลผลคำถามในคิวโดยอัตโนมัติ

หาก run ปัจจุบันถูก abort และยังมี คำถามที่เข้าคิว เหลืออยู่ บอตจะไม่ทำต่ออัตโนมัติ แต่จะถามว่าต้องการประมวลผลคำถามที่เหลือต่อหรือไม่ แบบรวมกันหรือทีละข้อ

## ⚠️ Diff (การเปลี่ยนไฟล์)

_ในแต่ละ การรันของเอเจนต์ บอตจะสร้าง สแนปช็อตก่อนและหลังการรัน แบบเบาของโปรเจกต์ด้วย เพื่อสรุปไฟล์ที่เปลี่ยนและส่ง diff กลับไปยัง Telegram ได้ สแนปช็อต นี้ถูกสร้างโดยตัวบอตเอง ไม่ใช่โดย Codex หรือ Copilot._

**สิ่งที่ควรรู้เกี่ยวกับ สแนปช็อต:**

- แอปจะสแกน ไดเรกทอรีโปรเจ็กต์ ก่อนและหลังการรัน
- สำหรับไฟล์ข้อความทั่วไป แอปจะใช้ diff จาก สแนปช็อต ของ run นั้นก่อน diff เทียบกับ git head
- โฟลเดอร์การพึ่งพา แคช และรันไทม์ที่พบบ่อยจะถูกข้ามเช่นกัน
- ไฟล์ binary และไฟล์ที่ใหญ่กว่า `SNAPSHOT_TEXT_FILE_MAX_BYTES` จะไม่ถูกอ่านเป็นข้อความ
- สำหรับโปรเจกต์ขนาดใหญ่มาก การสแกนเพิ่มนี้อาจเพิ่มภาระด้าน I/O และ memory ได้อย่างเห็นได้ชัด
- หาก สแนปช็อต ไม่สามารถแทนไฟล์เป็นข้อความได้ แอปจะ fallback ไปใช้ `git diff` เมื่อทำได้
- สำหรับไฟล์ขนาดใหญ่หรือไม่ใช่ข้อความ diff อาจถูกละไว้และแทนด้วยข้อความสั้น ๆ

กฎการยกเว้น snapshot อยู่ใน package resources:

- `src/coding_agent_telegram/resources/snapshot_excluded_dir_names.txt`
- `src/coding_agent_telegram/resources/snapshot_excluded_dir_globs.txt`
- `src/coding_agent_telegram/resources/snapshot_excluded_file_globs.txt`

คุณสามารถ override ค่าเหล่านี้ในไฟล์ env ได้โดยไม่ต้องแก้ package ที่ติดตั้งอยู่:

- `SNAPSHOT_INCLUDE_PATH_GLOBS`
  บังคับรวม path ที่ตรงเงื่อนไขเข้าไปใน diff
  ตัวอย่าง: `.github/*,.profile.test,.profile.prod`

- `SNAPSHOT_EXCLUDE_PATH_GLOBS`
  เพิ่มกฎยกเว้น diff เพิ่มเติมทับบนค่าเริ่มต้นของ package
  ตัวอย่าง: `.*,personal/*,sensitive*.txt`
  หมายเหตุ: `.*` จะตรงกับ path ที่ซ่อนอยู่ รวมถึงไฟล์ใน ไดเรกทอรีที่ซ่อนอยู่

หาก include และ exclude ตรงพร้อมกัน include จะมีผลก่อน

## 🌿 พฤติกรรมของ Branch

บอตถือว่า project และ branch เป็นชุดเดียวกัน

- การเลือก project จะไม่แอบเลือก branch ที่ไม่เกี่ยวข้องให้อัตโนมัติ
- หากต้องใช้ branch บอตจะถามให้คุณเลือก
- เมื่อมีการแสดงข้อมูล branch ในข้อความที่เกี่ยวกับเซสชัน จะโชว์ project และ branch ควบคู่กัน

เมื่อคุณสร้างหรือสลับ branch บอตจะพาคุณเลือก source อย่างชัดเจน:

- <code>local/&lt;branch&gt;</code> คือใช้ local branch เป็นต้นทาง
- <code>origin/&lt;branch&gt;</code> คืออัปเดตจาก remote branch ก่อน แล้วค่อยสลับ

ถ้าบอตพบว่า branch ที่เก็บไว้ในเซสชันไม่ตรงกับ branch ปัจจุบันของ repository บอตจะไม่ทำต่อแบบเดาสุ่ม แต่จะถามว่าต้องการใช้ branch ใด:

- ใช้ branch ที่เก็บไว้ในเซสชัน
- ใช้ branch ปัจจุบันของ repository

หาก source branch ที่คุณต้องการหายไป บอตจะเสนอ fallback source ตาม default branch และ current branch แทนที่จะปล่อยให้คุณเจอ Git error ตรง ๆ

## 🔐 พฤติกรรม trust ของ Git

- โฟลเดอร์ที่มีอยู่เดิมจะอิงตาม `CODEX_SKIP_GIT_REPO_CHECK`
- โฟลเดอร์ที่สร้างผ่าน `/project <name>` จะถูกทำเครื่องหมาย trusted โดยแอปนี้
- โฟลเดอร์เดิมที่เลือกผ่าน `/project <name>` จะยังคงเป็น untrusted จนกว่าคุณจะยืนยัน trust ใน Telegram
- ดังนั้นโฟลเดอร์โปรเจกต์ที่สร้างใหม่จึงใช้งานได้ทันที
- สามารถปิด `/commit` ได้ทั้งหมดด้วย `ENABLE_COMMIT_COMMAND`
- การทำ `/commit` ที่มีการแก้ไขจริงจะอนุญาตเฉพาะกับ trusted project เท่านั้น

## 🪵 บันทึก

log จะถูกเขียน **ทั้งไปที่ stdout และไฟล์ log แบบหมุนเวียน** ใต้ path นี้:

- `~/.coding-agent-telegram/logs` (หมุนเมื่อถึง 10 MB และเก็บสำรอง 3 ชุด)

> **หมายเหตุ:** ถ้าคุณดู terminal ไปพร้อมกับ tail ไฟล์ log ข้อความแต่ละอันจะปรากฏสองครั้ง นี่เป็นพฤติกรรมปกติ ควรดูอย่างใดอย่างหนึ่ง ไม่ใช่ทั้งสองพร้อมกัน

<details>
<summary><b>เหตุการณ์ที่มักถูกบันทึก</b></summary>

- การเริ่มต้น bot และเริ่ม polling
- การเลือก project
- การสร้างเซสชัน
- การสลับเซสชัน
- การรายงาน เซสชันที่ใช้งานอยู่
- การรันงานแบบปกติ (รวม audit log line ที่มี prompt แบบตัดทอน)
- การแทนที่เซสชันหลัง resume ล้มเหลว
- warnings และ runtime errors
</details>

## 🗂️ โครงสร้างโปรเจกต์

- `src/coding_agent_telegram/`
  โค้ดหลักของแอปพลิเคชัน

- `tests/`
  ชุดทดสอบ

- `startup.sh`
  entrypoint สำหรับ bootstrap และ startup แบบ local

- `src/coding_agent_telegram/resources/.env.example`
  template สภาพแวดล้อมหลักที่ใช้ทั้งตอนเริ่มจาก repo และตอนติดตั้งเป็น package

- `pyproject.toml`
  การตั้งค่า แพ็กเกจจิง และ dependencies

## 📦 การกำหนดเวอร์ชัน release

เวอร์ชันของ package ถูก derive จาก Git tags

- TestPyPI/testing: `v2026.3.26.dev1`
- PyPI prerelease: `v2026.3.26rc1`
- PyPI stable: `v2026.3.26`

## 📌 หมายเหตุ

- โปรเจกต์นี้ออกแบบมาสำหรับผู้ใช้ที่รัน agents แบบ local บนเครื่องของตนเอง
- Telegram bot เป็น control surface ไม่ใช่ execution environment
- หากคุณรันหลาย bot ก็ยังจัดการทั้งหมดได้ด้วย เซิร์ฟเวอร์โพรเซส เดียว
