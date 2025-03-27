const puppeteer = require('puppeteer');
const fs = require('fs');
const path = require('path');

async function gerarPDF(nomeArquivo) {
    try {


        // Obtém o caminho absoluto do arquivo
        const filePath = path.join(__dirname, 'temp_snapshot.txt');

        // Lê o arquivo txt
        const data = await fs.promises.readFile(filePath, 'utf8');

        // Extrai a key do snapshot (parte após os dois pontos)
        const snapshotKey = data.split(':')[1].trim();

        // Inicia o Puppeteer
        const browser = await puppeteer.launch({
            headless: true,
            executablePath: '/usr/bin/google-chrome',
            args: ['--incognito',
                '--disable-setuid-sandbox',
                '--disable-infobars',
                '--window-position=0,0',
                '--ignore-certifcate-errors',
                '--ignore-certifcate-errors-spki-list',
                '--no-sandbox',
            ]
        });

        const page = await browser.newPage();

        // Forçar tema light
        await page.emulateMediaFeatures([{ name: 'prefers-color-scheme', value: 'light' }]);

        await page.setViewport({ width: 1684, height: 1190 });

        // URL do snapshot do Grafana
        const url = `http://localhost:3002/dashboard/snapshot/${snapshotKey}?orgId=0&kiosk&theme=light`;

        // Navega até a página
        await page.goto(url, { waitUntil: 'networkidle0' });
        await new Promise(resolve => setTimeout(resolve, 5000));

        // Injetar CSS do tema light
        await page.addStyleTag({
            content: `
                .theme-dark { display: none !important; }
                .theme-light { display: block !important; }
                body { background: white !important; }
            `
        });

        // Ajusta o layout para maximizar o uso do espaço e move o conteúdo para a direita
        await page.evaluate(() => {
            document.body.style.overflow = 'hidden';
            document.body.style.margin = '0';
            document.body.style.padding = '0';

            const mainContent = document.querySelector('.react-grid-layout');
            if (mainContent) {
                const containerWidth = document.documentElement.clientWidth;
                const contentWidth = mainContent.scrollWidth;
                const scale = containerWidth / contentWidth;

                // Ajusta a escala e move para a direita
                mainContent.style.transform = `scale(${scale}) translateX(-220px)`; // Mova 50px para a direita
                mainContent.style.transformOrigin = 'top left';
                mainContent.style.width = `${100 / scale}%`;
                mainContent.style.height = `${100 / scale}%`;
            }

            // Remove elementos desnecessários
            const elementsToRemove = document.querySelectorAll('.navbar, .sidemenu, .submenu-controls');
            elementsToRemove.forEach(el => el.remove());

            // Ajusta o tamanho de todos os painéis
            const panels = document.querySelectorAll('.panel-container');
            panels.forEach(panel => {
                panel.style.overflow = 'hidden';
                const content = panel.querySelector('.panel-content');
                if (content) {
                    content.style.height = '100%';
                }
            });

            // Ajusta o container do dashboard, se existir
            const dashboardContainer = document.querySelector('.dashboard-container');
            if (dashboardContainer) {
                dashboardContainer.style.width = '100vw';
                dashboardContainer.style.height = '100vh';
                dashboardContainer.style.overflow = 'hidden';
            }
        });

        // Ajusta o posicionamento da página
        await page.evaluate(() => {
            const style = document.createElement('style');
            style.textContent = `
                body {
                    transform: translateY(-65px);
        
                }
            `;
            document.head.appendChild(style);
        });

        await page.pdf({
            path: nomeArquivo,
            format: 'A4',
            printBackground: true,
            margin: {
                top: '30px',
                right: '0mm',
                bottom: '0mm',
                left: '0mm'
            },
            // scale: 0.37 // Corresponde à escala definida no CSS
        });

        console.log(`PDF gerado com sucesso: ${nomeArquivo}`);
        await browser.close();

    } catch (error) {
        console.error('Erro:', error);
        throw error;
    }
}

// Pega o argumento da linha de comando (nome do arquivo)
const nomeArquivo = process.argv[2];

if (nomeArquivo) {
    gerarPDF(nomeArquivo)
        .catch(error => {
            console.error('Erro:', error);
            process.exit(1);
        });
} else {
    console.error('Por favor, forneça o nome do arquivo');
    process.exit(1);
}