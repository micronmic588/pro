const axios = require('axios');
const fs = require('fs-extra');
const path = require('path');

// Define the history file path
const HISTORY_FILE = path.join(__dirname, '..', 'database', 'chathistory', 'blackbox.json');

// Ensure the directory exists
fs.ensureDirSync(path.dirname(HISTORY_FILE));

let userHistories = {};

// Load chat histories from file if it exists, otherwise create an empty file
if (fs.existsSync(HISTORY_FILE)) {
    userHistories = fs.readJsonSync(HISTORY_FILE);
} else {
    fs.writeJsonSync(HISTORY_FILE, userHistories, { spaces: 2 });
}

// Save chat histories to file periodically
setInterval(() => {
    fs.writeJsonSync(HISTORY_FILE, userHistories, { spaces: 2 });
}, 300000); // every 5 minutes

// Bot command configuration
module.exports.config = {
    name: "blackbox",
    description: "Interact with Blackbox AI for code assistance",
    usage: "/blackbox <query>",
    role: "user",
    usePrefix: true,
    aliases: [],
    author: "MICRON",
};

module.exports.run = async function ({ bot, chatId, args, history, msg }) {
    const query = args.join(' ');
    const userId = msg.from.id;

    if (!query) {
        return bot.sendMessage(chatId, "Please provide a query.");
    }

    try {
        const result = await sendRequest(query, userId);
        const sentMsg = await bot.sendMessage(chatId, result);
        return sentMsg; // Return the sent message object
    } catch (error) {
        console.error("Error:", error.message);
        return bot.sendMessage(chatId, "An error occurred while making the API request. Please try again later.");
    }
};

module.exports.onReply = async function ({ bot, chatId, userMessage, history, msg }) {
    const userId = msg.from.id;

    try {
        const result = await sendRequest(userMessage, userId);
        const sentMsg = await bot.sendMessage(chatId, result);
        return sentMsg; // Return the sent message object
    } catch (error) {
        console.error("Error:", error.message);
        return bot.sendMessage(chatId, "An error occurred while making the API request. Please try again later.");
    }
};

async function sendRequest(query, userId) {
    // Update chat history
    if (!userHistories[userId]) {
        userHistories[userId] = [];
    }
    userHistories[userId].push(`User: ${query}`);

    // Prepare the request payload for the Blackbox API
    const data = {
        messages: userHistories[userId].map(text => ({ role: "user", content: text })),
        id: "2qS8Ibm",
        codeModelMode: true,
        agentMode: {},
        trendingAgentMode: {}
    };

    const options = {
        method: 'POST',
        url: 'https://www.blackbox.ai/api/chat',
        headers: { 
            'Content-Type': 'application/json'
        },
        data
    };

    // Make the request to Blackbox AI
    const response = await axios.request(options);

    if (response.status === 200) {
        const respText = cleanText(response.data);
        userHistories[userId].push(`Blackbox: ${respText}`);
        return respText;
    } else {
        throw new Error(`API responded with status ${response.status}`);
    }
}

// Function to clean up response text similar to the Python version
function cleanText(text) {
    return text.replace(/\$~\$.*?\$~\$|\$~~\$.*?\$~~\$|\$~~~\$.*?\$~~~\$|\$@\$.*/, '').trim();
}
