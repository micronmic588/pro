const axios = require('axios');
const fs = require('fs');

module.exports.config = {
    name: "emi",
    description: "Text to Image",
    usage: "/emi <prompt>",
    role: "user",
    usePrefix: true,
    author: "MICRON",
};

module.exports.run = async function ({ bot, chatId, args }) {
    const text = args.join(' ');

    if (!text) {
        return bot.sendMessage(chatId, "do your own work");
    }

    const generatingMessage = await bot.sendMessage(chatId, "Generating, please wait...");
    
    const formattedText = `*Prompt:* _${text}_`;

    const baseURL = `https://sandipbaruwal.onrender.com/emi?prompt=${encodeURIComponent(text)}`;

    try {
        const response = await axios.get(baseURL, { responseType: 'stream' });
        const path = `emi_image_${Date.now()}.jpg`;
        const writer = fs.createWriteStream(path);

        response.data.pipe(writer);

        await new Promise((resolve, reject) => {
            writer.on('finish', resolve);
            writer.on('error', reject);
        });

        await bot.sendPhoto(chatId, path, { caption: formattedText, parseMode: 'Markdown' });
        fs.unlinkSync(path);

        // Delete the "Generating" message after sending the photo
        bot.deleteMessage(chatId, generatingMessage.message_id);
    } catch (error) {
        console.error(error);
        bot.sendMessage(chatId, "❌ Failed to generate the image");
        // Delete the "Generating" message if an error occurs
        bot.deleteMessage(chatId, generatingMessage.message_id);
    }
};
