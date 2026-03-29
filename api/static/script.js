// 🌗 THEME TOGGLE (GLOBAL)
function toggleTheme() {
    document.body.classList.toggle("light-mode");

    const btn = document.querySelector(".theme-toggle");

    if (document.body.classList.contains("light-mode")) {
        localStorage.setItem("theme", "light");
        if (btn) btn.textContent = "🌙";
    } else {
        localStorage.setItem("theme", "dark");
        if (btn) btn.textContent = "🌗";
    }
}

window.onload = function () {
    console.log("App Loaded 🚀");

    const codeBox = document.getElementById("code");
    const runBtn = document.getElementById("run");
    const stepBtn = document.getElementById("step");
    const assembleBtn = document.getElementById("assemble");
    const resetBtn = document.getElementById("reset");

    const memory = document.getElementById("memory-container");
    const registers = document.getElementById("registers-flags");
    const assembler = document.getElementById("assembler-container");
    const track = document.getElementById("track");

    if (!codeBox) return console.error("UI elements not found!");

    // 🌗 Load saved theme + fix button icon
    const savedTheme = localStorage.getItem("theme");
    const btn = document.querySelector(".theme-toggle");

    if (savedTheme === "light") {
        document.body.classList.add("light-mode");
        if (btn) btn.textContent = "🌙";
    } else {
        if (btn) btn.textContent = "🌗";
    }

    // Load saved code
    codeBox.value = localStorage.getItem("code") || "";

    if (runBtn) runBtn.disabled = true;
    if (stepBtn) stepBtn.disabled = true;

    // 🔥 Keyboard shortcut: Ctrl+Enter = Run
    document.addEventListener("keydown", function (e) {
        if (e.ctrlKey && e.key === "Enter") {
            runBtn && !runBtn.disabled && runBtn.click();
        }
    });

    function showLoading() {
        if (assembler) assembler.innerHTML = "<div class='card'><p>⏳ Running...</p></div>";
    }

    function animate(el) {
        if (!el) return;
        el.style.transform = "scale(1.03)";
        setTimeout(() => (el.style.transform = "scale(1)"), 200);
    }

    function updateUI(data) {
        if (!data) return;

        if (registers)
            registers.innerHTML = wrapCard("Registers", data.registers_flags);

        if (memory)
            memory.innerHTML = wrapCard("Memory", data.memory);

        if (assembler)
            assembler.innerHTML = wrapCard("Assembler", data.assembler);

        animate(memory);
        animate(registers);
    }

    // 🎯 Card Wrapper
    function wrapCard(title, content) {
        return `
        <div class="card">
            <h3>${title}</h3>
            <div>${content}</div>
        </div>`;
    }

    // 🧠 Read flag checkboxes
    function getFlags() {
        const flags = {};
        document.querySelectorAll(".flag-input").forEach(el => {
            flags[el.id] = el.checked;
        });
        return flags;
    }

    // 📊 Progress Tracker
    function updateProgress(code, index) {
        const lines = code.split("\n");
        let output = "";
        lines.forEach((_, i) => {
            if (i < index) output += "🟢\n";
            else if (i === index) output += "🟡\n";
            else output += "⚪\n";
        });
        if (track) track.value = output;
    }

    // 🔧 ASSEMBLE
    assembleBtn && assembleBtn.addEventListener("click", async function () {
        const code = codeBox.value.trim();
        if (!code) return alert("Enter some 8051 assembly code first!");

        localStorage.setItem("code", code);
        showLoading();

        try {
            const res = await fetch("/assemble", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ code: code, flags: getFlags() })
            });

            const data = await res.text();
            if (!res.ok) throw new Error(data);

            if (memory) memory.innerHTML = data;
            if (runBtn) runBtn.disabled = false;
            if (stepBtn) stepBtn.disabled = false;
            updateProgress(code, 0);
            animate(memory);

        } catch (err) {
            alert("Assemble error:\n" + err.message);
        }
    });

    // ▶ RUN ALL
    runBtn && runBtn.addEventListener("click", async function () {
        showLoading();
        try {
            const res = await fetch("/run", {
                method: "POST",
                headers: { "Content-Type": "text/plain" }
            });

            if (!res.ok) {
                const err = await res.text();
                throw new Error(err);
            }

            const data = await res.json();
            updateUI(data);
            const code = codeBox.value.trim();
            updateProgress(code, code.split("\n").filter(Boolean).length);

        } catch (err) {
            alert("Run error:\n" + err.message);
            console.error(err);
        }
    });

    // 🔁 STEP (run one instruction)
    stepBtn && stepBtn.addEventListener("click", async function () {
        showLoading();
        try {
            const res = await fetch("/run-once", {
                method: "POST",
                headers: { "Content-Type": "text/plain" }
            });

            if (!res.ok) {
                const err = await res.text();
                throw new Error(err);
            }

            const data = await res.json();
            updateUI(data);
            updateProgress(codeBox.value.trim(), data.index);

        } catch (err) {
            alert("Step error:\n" + err.message);
        }
    });

    // 🔄 RESET
    resetBtn && resetBtn.addEventListener("click", async function () {
        try {
            const res = await fetch("/reset", { method: "POST" });
            if (!res.ok) throw new Error(await res.text());

            const data = await res.json();
            updateUI(data);

            if (runBtn) runBtn.disabled = true;
            if (stepBtn) stepBtn.disabled = true;
            if (track) track.value = "";

        } catch (err) {
            alert("Reset error:\n" + err.message);
        }
    });

    // ✏️ MEMORY EDIT — supports "30H=12H", "0x30=0x12", "30=12"
    const memEditInput = document.getElementById("memory_edit_input");
    if (memEditInput) {
        // Show hint on focus
        memEditInput.addEventListener("focus", function () {
            if (!memEditInput.placeholder) return;
        });

        memEditInput.addEventListener("keydown", async function (e) {
            if (e.key !== "Enter") return;
            const raw = memEditInput.value.trim();
            if (!raw) return;

            const normalise = s => {
                s = s.trim().toUpperCase();
                if (s.endsWith("H")) s = "0x" + s.slice(0, -1);
                if (!s.startsWith("0X") && !s.startsWith("0x")) s = "0x" + s;
                return s.toLowerCase();
            };

            const parts = raw.split("=");
            if (parts.length !== 2) {
                alert("Format: ADDR=VALUE\nExamples:\n  0030H=12H\n  0x30=0x12\n  30=12");
                return;
            }

            try {
                const addr = normalise(parts[0]);
                const val  = normalise(parts[1]);
                const res = await fetch("/memory-edit", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify([[addr, val]])
                });
                if (!res.ok) throw new Error(await res.text());
                const data = await res.json();
                updateUI(data);
                memEditInput.value = "";
                animate(memory);
            } catch (err) {
                alert("Memory edit failed:\n" + err.message);
            }
        });
    }
};
