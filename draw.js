const axios = require('axios');
const fs = require('fs');

module.exports.config = {
    name: "draw",
    description: "Generate an image based on a prompt",
    usage: "/draw <prompt>",
    role: "user",
    usePrefix: true,
    aliases: ["image","gitstalk"],
    author: "MICRON",
};

module.exports.run = async function ({ bot, chatId, args }) {
    const prompt = args.join(' ');

    if (!prompt) {
        return bot.sendMessage(chatId, "😡 Please provide a prompt.");
    }

    const baseURL = 'https://api.creartai.com/api/v1/text2image';

    // Send the "Generating" message and store its message ID
    // const generatingMessage = await bot.sendMessage(chatId, "✅ Generating, please wait...");

    const formattedText = `*Prompt:* _${prompt}_`;

    const options = {
        method: 'POST',
        url: baseURL,
        headers: {
            'Content-Type': 'application/x-www-form-urlencoded'
        },
        data: new URLSearchParams({
            prompt: prompt,
            negative_prompt: ',malformed hands,malformed fingers,malformed faces,malformed body parts,mutated body parts,malfromed eyes,mutated fingers,mutated hands,realistic,worst quality, low quality, blurry, pixelated, extra limb, extra fingers, bad hand, text, name, letters, out of frame, lowres, text, error, cropped, jpeg artifacts, ugly, duplicate, morbid, mutilated, out of frame, mutated hands, poorly drawn hands, poorly drawn face, mutation, deformed, blurry, dehydrated, bad anatomy, bad proportions, extra limbs, cloned face, disfigured, gross proportions, malformed limbs, missing arms, missing legs, extra arms, extra legs, fused fingers, too many fingers, long neck, username,',
            aspect_ratio: '3x3',
            num_outputs: '',
            num_inference_steps: '',
            controlnet_conditioning_scale: 0.5,
            guidance_scale: '5.5',
            scheduler: '',
            seed: ''
        })
    };

    try {
        const response = await axios(options);
        const imageData = response.data.image_base64;
        const imageBuffer = Buffer.from(imageData, 'base64');
        const path = `images/${Date.now()}.jpg`;

        fs.writeFileSync(path, imageBuffer);

        await bot.sendPhoto(chatId, path, { caption: formattedText, parseMode: 'Markdown' });

        fs.unlinkSync(path);

        // Delete the "Generating" message after sending the photo
        bot.deleteMessage(chatId, generatingMessage.message_id);
    } catch (error) {
        console.error(error);
        bot.sendMessage(chatId, "❌ Failed to generate the image. Please try again later.");
        // Delete the "Generating" message if an error occurs
        bot.deleteMessage(chatId, generatingMessage.message_id);
    }
};
