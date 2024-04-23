const venom = require('venom-bot');
const net = require('net');


//const numero_caique = '27996162054@c.us'
//const numero_andre = '2799438898@c.us'


venom
    .create(
        //session
        { session: 'sessionName' }, //Pass the name of the client you want to start the bot
        //catchQR
        (base64Qrimg, asciiQR, attempts, urlCode) => {
            console.log('Number of attempts to read the qrcode: ', attempts);
            console.log('Terminal qrcode: ', asciiQR);
            //console.log('base64 image string qrcode: ', base64Qrimg);
            //console.log('urlCode (data-ref): ', urlCode);
        },
        // statusFind
        (statusSession, session) => {
            console.log('Status Session: ', statusSession); //return isLogged || notLogged || browserClose || qrReadSuccess || qrReadFail || autocloseCalled || desconnectedMobile || deleteToken || chatsAvailable || deviceNotConnected || serverWssNotConnected || noOpenBrowser || initBrowser || openBrowser || connectBrowserWs || initWhatsapp || erroPageWhatsapp || successPageWhatsapp || waitForLogin || waitChat || successChat
            //Create session wss return "serverClose" case server for close
            console.log('Session name: ', session);
        },
        // options
        {
            browserPathExecutable: '/usr/bin/chromium', // browser executable path
            headless: 'new', // you should no longer use boolean false or true, now use false, true or 'new' learn more https://developer.chrome.com/articles/new-headless/
            browserArgs: [''], // Original parameters  ---Parameters to be added into the chrome browser instance
            addBrowserArgs: [''], // Add broserArgs without overwriting the project's original
            devtools: false,
            debug: false,
            logQR: false,
            updatesLog: true,
            autoClose: 0,
            createPathFileToken: true,
        },

        // BrowserInstance
        (browser, waPage) => {
            console.log('Browser PID:', browser.process().pid);
            waPage.screenshot({ path: 'screenshot.png' });
        }
    )
    .then((client) => {
        start(client);
    })
    .catch((erro) => {
        console.log(erro);
    });

// Função para iniciar o cliente do Venom-bot
function start(client) {
    const server = net.createServer((socket) => {
        console.log('Conexão estabelecida');

        socket.on('data', (data) => {
            const [numero, mensagem] = data.toString().split('$');
            console.log('Numero recebida: ', numero);
            console.log('Mensagem recebida: ', mensagem);
            
            //Mensagem para numero 1
            client.sendText(numero, mensagem)
            .then(() => {
                console.log('Mensagem enviada com sucesso');
                socket.end(); // Encerra a conexão após enviar a mensagem

            })
            .catch((error) => {
                console.error('Erro ao enviar mensagem:', error);
                socket.end(); // Encerra a conexão após enviar a mensagem

            });

        });

        socket.on('end', () => {
            console.log('Conexão encerrada');
        });
    });

    const PORT = 65432;
    server.listen(PORT, () => {
        console.log(`Servidor escutando na porta ${PORT}`);
    });
}