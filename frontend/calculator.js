// These names become XML IDs. server.py uses them to choose the Python maths class.
const OPERATORS = { "+": "Plus", "−": "Minus", "×": "Multiplication", "÷": "Division" };
const KEYBOARD_KEYS = { "*": "×", "/": "÷", "-": "−", "Enter": "=", "Backspace": "⌫", "Escape": "C" };

// These variables hold the current sum, the previous sum and any error.
// parts contains strings, e.g. ["2", "+", "3", "×", "4"]. Python does the maths.
let parts = [];
let lastSum = "";
let errorMessage = "";

// These are the actual elements in index.html. Changing textContent changes their text.
const screenElement = document.getElementById("screen");
const lastSumLine = document.getElementById("last-sum");
const sentXmlBox = document.getElementById("sent-xml");
const replyXmlBox = document.getElementById("reply-xml");
const buttons = [...document.querySelectorAll(".buttons button")];

// Mouse and keyboard both call press(), so they follow the same input rules.
for (const button of buttons) {
    button.addEventListener("click", () => press(button.textContent));
}
window.addEventListener("keydown", (event) => {
    const label = KEYBOARD_KEYS[event.key] || event.key;
    if (buttons.some((button) => button.textContent === label)) {
        event.preventDefault();
        press(label);
    }
});

async function press(button) {
    const openBrackets = parts.filter((part) => part === "(").length - parts.filter((part) => part === ")").length;
    if (button === "=") {
        const last = parts[parts.length - 1];
        // Need a complete sum before sending it.
        if (!parts.some((part) => OPERATORS[part]) || OPERATORS[last] || last === "(") return;

        // Close any brackets the user forgot. buildXmlTree groups the maths and writes the XML.
        const fullParts = [...parts];
        for (let i = 0; i < openBrackets; i++) fullParts.push(")");
        const xml = '<?xml version="1.0" encoding="UTF-8"?>\n<Maths>\n' + buildXmlTree(fullParts) + "</Maths>";
        sentXmlBox.textContent = xml;
        replyXmlBox.textContent = "Waiting for the server...";
        lastSum = fullParts.join(" ").replaceAll("( ", "(").replaceAll(" )", ")") + " =";
        updateScreen();

        try {
            const response = await fetch("/", { method: "POST", headers: { "Content-Type": "application/xml" }, body: xml });
            const replyText = await response.text();
            const reply = new DOMParser().parseFromString(replyText, "application/xml");
            replyXmlBox.textContent = replyText;
            if (response.ok) {
                // Keep the answer. The next operator can use it.
                parts = [reply.querySelector("Answer").textContent];
            } else {
                parts = [];
                errorMessage = reply.querySelector("Error").textContent;
            }
        } catch {
            parts = [];
            replyXmlBox.textContent = "-";
            errorMessage = "Could not reach the server. Is server.py running?";
        }
        updateScreen();
        return;
    }

    // Work on a copy. If a button is not allowed, return without changing the sum.
    let newParts = [...parts];
    // After =, a digit or opening bracket starts over. An operator uses the answer.
    if (lastSum !== "" && ("0123456789.".includes(button) || button === "(")) newParts = [];
    const last = newParts[newParts.length - 1];
    const lastIsNumber = !isNaN(last); // True for "12", "0." and "-3".

    if (button === "C") {
        newParts = [];
    } else if (button === "⌫") {
        if (last === undefined) return;
        const shorter = last.slice(0, -1);
        // Drop broken numbers. Drop E answers whole so their exponent cannot grow.
        if (shorter === "" || isNaN(shorter) || last.includes("E")) newParts.pop();
        else newParts[newParts.length - 1] = shorter;
    } else if (OPERATORS[button]) {
        // Need a number first. Replace the previous operator if there is one.
        if (last === undefined || last === "(") return;
        if (OPERATORS[last]) newParts.pop();
        newParts.push(button);
    } else if (button === ")") {
        if (openBrackets === 0 || (!lastIsNumber && last !== ")")) return;
        newParts.push(")");
    } else if (button === "(") {
        // 2(3 + 4) means 2 × (3 + 4).
        if (lastIsNumber || last === ")") newParts.push("×");
        newParts.push("(");
    } else if (lastIsNumber) {
        // Grow the number. Block extra dots and edits to E answers.
        if (isNaN(last + button) || last.includes("E")) return;
        newParts[newParts.length - 1] = last + button;
    } else {
        // (2 + 3)4 means (2 + 3) × 4.
        if (last === ")") newParts.push("×");
        newParts.push(button === "." ? "0." : button);
    }

    parts = newParts;
    lastSum = "";
    errorMessage = "";
    updateScreen();
}

function updateScreen() {
    // The variables changed. Copy their current values onto the page.
    lastSumLine.textContent = lastSum;
    screenElement.textContent = errorMessage || parts.join(" ").replaceAll("( ", "(").replaceAll(" )", ")") || "0";
    screenElement.classList.toggle("error", errorMessage !== "");
}

function buildXmlTree(parts, indent = "    ", parentName = "") {
    // Return XML text directly. server.py reads these tags to make the Python maths objects.
    // Split at + or − first, putting × and ÷ in inner groups that Python calculates first.
    // Scan from the right so equal-priority operators are calculated left to right.
    // Example: 8 ÷ 2 × 2 becomes (8 ÷ 2) × 2, not 8 ÷ (2 × 2).
    for (const operators of [["+", "−"], ["×", "÷"]]) {
        let depth = 0;
        for (let i = parts.length - 1; i >= 0; i--) {
            // Skip operators inside brackets. Their group is built in a later recursive call.
            if (parts[i] === ")") depth++;
            if (parts[i] === "(") depth--;
            if (depth === 0 && operators.includes(parts[i])) {
                const name = OPERATORS[parts[i]];
                // 2 + 3 + 4 stays one Plus tag with three values. parentName is the
                // enclosing operation's name; a repeated left-side operation joins it.
                const joinParent = name === parentName;
                const inputIndent = joinParent ? indent : indent + "    ";
                const leftXml = buildXmlTree(parts.slice(0, i), inputIndent, name);
                const rightXml = buildXmlTree(parts.slice(i + 1), inputIndent);
                if (joinParent) return leftXml + rightXml;
                return indent + '<Operation ID="' + name + '">\n' + leftXml + rightXml + indent + "</Operation>\n";
            }
        }
    }

    // One number becomes a Value tag. Otherwise remove the outer brackets and recurse.
    // Leave out parentName so a bracket group keeps its own tag, e.g. 10 − (3 − 2).
    if (parts[0] !== "(") return indent + "<Value>" + parts[0] + "</Value>\n";
    return buildXmlTree(parts.slice(1, -1), indent);
}
