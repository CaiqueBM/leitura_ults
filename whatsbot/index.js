const venom = require('venom-bot');
const net = require('net');
const fs = require('fs');
const grupo = '/home/abs/Aplicativos/leitura_ults/whatsbot/grupo.txt';


//const numero_caique = '27996162054@c.us'
//const numero_andre = '2799438898@c.us'


function iniciaBot()
{
	venom
		.create(
			//session
			{ session: 'Bot ABS' }, //Pass the name of the client you want to start the bot
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
			setTimeout(iniciaBot, 30000);
		});
}
// Função para iniciar o cliente do Venom-bot
function start(client) 
{
	
	/* ------------------------------ 
	--- SOCKET DE INTERFACE E ENVIO DE MSG
	*/
	const server = net.createServer((socket) => 
	{
		console.log('Conexão estabelecida');
		socket.on('data', (data) => 
		{
			const [numero, mensagem] = data.toString().split('$');
			console.log('Numero recebida:', numero);
			console.log('Mensagem recebida:', mensagem);
			
			//Mensagem para numero 1
			if (mensagem[0] === '#')
			{
				switch (mensagem[1])
				{
					case 'L':
						//Manda localização
						const [lat,lon,txt] = mensagem.slice(2).split(';');
						client.sendLocation(numero,lat,lon,txt);
						socket.end();
						break;
					default:
				}
			}
			else 
			{
				client.sendText(numero, mensagem)
				.then(() => {
								console.log('Mensagem enviada com sucesso');
								socket.end(); // Encerra a conexão após enviar a mensagem
							})
				.catch((error) => {
									console.error('Erro ao enviar mensagem :', error);
									socket.end(); // Encerra a conexão após enviar a mensagem
									});
			}
		});
		socket.on('end', () => 
		{
			console.log('Conexão encerrada');
		});
	});
	const PORT = 65432;
	server.listen(PORT, () => 
	{
		console.log(`Servidor escutando na porta ${PORT}`);
	});
	
	/* ------------------------------ 
		--- TRATATIVAS DE MENSAGENS RECEBIDAS
	--------------------------------*/
	//Bot Entra no grupo
	client.onMessage((message) => 
	{
		if (message.body === 'Bot ativa grupo!' && message.isGroupMsg === true) 
		{
			client.sendText(message.from,'Grupo ' + message.from + ' Ativado');
			fs.writeFile(grupo, message.from, (erro) =>
			{
				if (erro) { console.error("Erro ao escrever no arquivo", (erro))}
				else { console.log("Novo grupo atualizado " + message.from) }
			});
		}
		else if (message.body === 'Bot sai do grupo!' && message.isGroupMsg === true)
		{
			client.sendText(message.from,'Saindo do grupo '+ message.from);
			client.leaveGroup(message.from);
			fs.writeFile(grupo, '', (erro) =>
			{
				if (erro) { console.error("Erro ao escrever no arquivo", (erro))}
				else { console.log("Grupo descartado do registro " + message.from) }
			});
		}
	});
	/* ------------------------------ 
		--- TRATATIVAS DE DESCONEXAO
	--------------------------------*/
	
	//MUDANÇA DE ESTADO
	client.onStateChange((state) => 
	{
		console.log('State changed: ', state);
		// force whatsapp take over
		if ('CONFLICT'.includes(state)) client.useHere();
			// detect disconnect on whatsapp
		if ('UNPAIRED'.includes(state))
		{
			console.log('logout, reiniciando o bot em 30s');
			setTimeout(iniciaBot, 30000);
		}
	});
	//MUDANÇA DE CONEXAO.
	let time = 0;
	client.onStreamChange((state) => 
	{
		console.log('State Connection Stream: ' + state);
		clearTimeout(time);
		if (state === 'DISCONNECTED' || state === 'SYNCING') 
		{
			time = setTimeout(() => 
			{
				client.close();
				setTimeout(iniciaBot, 30000);
			}, 80000);
		}
	});
	//Fechando graciosamente.
	process.on('SIGINT', function() 
	{
		client.close();
	});
}

//Por fim rode o bot quando for chamado.
iniciaBot();
