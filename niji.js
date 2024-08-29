const axios = require('axios');
const fs = require('fs');

module.exports.config = {
    name: "niji",
    description: "Generate an image using the Niji AI",
    usage: "/niji <prompt>",
    role: "user",
    usePrefix: true,
    aliases: ["insta", "fb"],
    author: "MICRON"
};

module.exports.run = async function ({ bot, chatId, args }) {
    const prompt = args.join(' ');

    if (!prompt) {
        return bot.sendMessage(chatId, "Please provide a prompt.");
    }

    const generatingMessage = await bot.sendMessage(chatId, "✅ Generating, please wait...");
    const sessionHash = "kuccpb8c89s";

    try {
        let attempts = 0; 

        const generateImage = async () => {
            try {
                // Step 1: Send POST request
                const postUrl = 'https://linaqruf-animagine-xl.hf.space/queue/join?';
                const postData = {
                        data: [prompt, "", 2128329701, 1024, 1024, 12, 30, "DPM++ 2M Karras", "1024 x 1024", "(None)", "Heavy", true, 0.55, 1.5, true],
                        event_data: null,
                        fn_index: 5,
                        trigger_id: 7,
                        session_hash: sessionHash
                };

                await axios.post(postUrl, postData, {
                        headers: { 'Content-Type': 'application/json', 'Connection': 'keep-alive' },
                        timeout: 5000
                });

                // Step 2: Polling loop and saving response to a file
                let processCompleted = false;
                while (!processCompleted) {
                    const getResponse = await axios.get(`https://linaqruf-animagine-xl.hf.space/queue/data?session_hash=${sessionHash}`, {
                        timeout: 5000,
                        responseType: 'json' // Change to 'json' for easier parsing
                    });

                    fs.writeFileSync('nijiResponse.json', JSON.stringify(getResponse.data, null, 2));

                    const eventData = JSON.parse(fs.readFileSync('nijiResponse.json', 'utf8'));
                    
                    if (eventData.msg === 'process_completed') {
                        processCompleted = true;
                        // Extract image data correctly from eventData
                        const imageUrl = eventData.output.data[0][0].image.url;
                        
                        // Step 3: Send image to Telegram (adapt this part from your gen.js)
                        // You would download the image and then use bot.sendPhoto(chatId, photoPath);
                    }

                    if (!processCompleted) {
                        await new Promise(resolve => setTimeout(resolve, 2000));
                    }
                }

            } catch (error) {
                if (error.code === 'ECONNRESET' && attempts < 3) {
                    attempts++;
                    console.error('Connection reset, retrying...', attempts);
                    await new Promise(resolve => setTimeout(resolve, 2000)); 
                    return generateImage();
                } else if (error.code === 'ERR_BAD_RESPONSE') {
                    console.error('Unexpectedly large response. Consider streaming if this continues.');
                } else {
                    throw error; // Let other errors be handled below
                }
            }
        }

        await generateImage();

    } catch (error) {
        console.error('Error generating image:', error);
        bot.sendMessage(chatId, "❌ Failed to generate the image. Please try again later.");
        bot.deleteMessage(chatId, generatingMessage.message_id);
    }
};
