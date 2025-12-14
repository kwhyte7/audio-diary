# My audio journal project

Haven't thought of a proper name for this yet.

I want to make a simple little audio journal that lets me talk into a microphone/record or upload an audio file, where then `faster-whisper` then transcribes the uploaded recording. Then, it will be lightly formatted by an LLM, to maintain legibility.

This'll host it as a website, and when running you should be able to access it from your browser.

## Security & Encryption

I'm thinking of options for encryption, like encrypting your files behind a passphrase you create. This'll be optional and for extra security.

I'll also make some sort of account system, so when hosting you can host it on one server and let other people use it.

When hosting, you might want to have SSL encryption using caddy or nginx + certbot. I'm a new coder, so I'm not planning on doing all that.






