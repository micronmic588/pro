const axios = require('axios');

module.exports.config = {
    name: "gemini",
    description: "Ask a question and get a response",
    usage: "/ask <your_question>",
    role: "user",
    usePrefix: true,
    aliases: ["image"],
    author: "OtinXSandip",
};

module.exports.run = async function ({ bot, chatId, args }) {
    // Check if a question is provided
    if (!args[0]) {
        bot.sendMessage(chatId, `⚠️ Please provide a question.\n💡 Usage: ${this.config.usage}`);
        return;
    }

    const question = args.join(" ");

    // Send a pre-processing message
    const preMessage = await bot.sendMessage(chatId, "💭 | Thinking...");

    try {
        const encodedQuestion = encodeURIComponent(question);
        const res = await axios.get(`https://sandipbaruwal.onrender.com/gemini?prompt=${encodedQuestion}`);
        const result = res.data.answer;

        // Detect code format and include in a code block
        const formattedResponse = result.match(/```(\w+)\n([\s\S]+)```/) ?
            result : "\n```\n" + result + "\n```";

        bot.sendMessage(chatId, formattedResponse, { parseMode: 'Markdown' });
    } catch (error) {
        console.error("Error:", error.message);
        bot.sendMessage(chatId, "Failed to process the question. Please try again later.");
    } finally {
        // Delete the pre-processing message
        bot.deleteMessage(chatId, preMessage.message_id);
    }
};
