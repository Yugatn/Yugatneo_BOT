const statusNode = document.getElementById("status");
const resultNode = document.getElementById("result");
const codeNode = document.getElementById("verification-code");
const copyButton = document.getElementById("copy-code");
const params = new URLSearchParams(window.location.search);
const ticket = params.get("ticket") || "";
const signature = params.get("signature") || "";

window.onHumanChallengePassed = async function(token) {
  if (!ticket || !signature) {
    statusNode.textContent = "Ссылка проверки неполная. Вернись в исходный чат и запроси новую ссылку.";
    return;
  }
  statusNode.textContent = "Проверяем результат…";
  try {
    const response = await fetch("/human/verify", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({ticket, signature, turnstile_token: token})
    });
    const body = await response.json();
    if (!response.ok) throw new Error(body.detail || "Проверка не прошла");
    codeNode.textContent = body.one_time_code;
    resultNode.hidden = false;
    statusNode.textContent = "Готово. Код действует 5 минут.";
  } catch (error) {
    statusNode.textContent = error.message || "Не удалось завершить проверку. Запроси новую ссылку в боте.";
  }
};

window.onHumanChallengeExpired = function() {
  statusNode.textContent = "Проверка истекла. Выполни её ещё раз.";
};

copyButton.addEventListener("click", async () => {
  try {
    await navigator.clipboard.writeText(codeNode.textContent);
    copyButton.textContent = "Скопировано";
  } catch {
    statusNode.textContent = "Выдели код и скопируй его вручную.";
  }
});
