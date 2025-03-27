const puppeteer = require('puppeteer'); // v23.0.0 or later
const fs = require('fs');

async function clicarBotao2025(page) {
    try {
        // Espera pelo botão com a classe accordion-button
        await page.waitForSelector('button.accordion-button', { visible: true });

        // Clica no botão que contém o texto "2025"
        const clicado = await page.evaluate(() => {
            const botoes = Array.from(document.querySelectorAll('button.accordion-button'));
            const botao2025 = botoes.find(b => b.textContent.trim() === '2025');
            if (botao2025) {
                botao2025.click();
                return true;
            }
            return false;
        });

        if (clicado) {
            // console.log('Botão 2025 clicado com sucesso');
            // Espera um pouco para a animação do accordion
            return true;
        } else {
            console.log('Botão 2025 não encontrado');
            return false;
        }
    } catch (error) {
        console.error('Erro ao clicar no botão 2025:', error);
        return false;
    }
}

async function extrairDadosTabela(page) {
    try {
        // Espera a tabela aparecer após o clique
        await page.waitForSelector('.table.table-1', { visible: true });
        // Extrai os dados
        const dados = await page.evaluate(() => {
            const mesAtual = new Date().getMonth() + 1; // Mês atual (1-12)
            const dados = [];

            for (let i = 1; i <= mesAtual; i++) {
                const linha = document.querySelector(`.table.table-1 tbody tr:nth-child(${i + 1})`);
                if (!linha) continue;

                const celulas = linha.querySelectorAll('td');
                dados.push({
                    mes: celulas[0]?.textContent.trim(),
                    pis: celulas[1]?.textContent.trim(),
                    cofins: celulas[2]?.textContent.trim(),
                    total: celulas[3]?.textContent.trim()
                });
            }

            return dados;
        });

        if (dados.length > 0) {
            const nomeArquivo = 'imposto.json';
            const dadosFormatados = dados.map(item => ({
                mes: item.mes.split('/')[0],
                pis_pasep: item.pis,
                cofins: item.cofins,
                total: item.total
            }));

            fs.writeFileSync(nomeArquivo, JSON.stringify(dadosFormatados, null, 2));
            console.log(`Dados salvos em ${nomeArquivo}`);
        } else {
            console.log('Nenhum dado encontrado.');
        }














        // // Extrai os dados
        // const dados = await page.evaluate(() => {
        //     const mesAtual = new Date().getMonth() + 1;
        //     const childIndex = mesAtual + 1;

        //     // Pega a segunda linha da tabela (primeira é o cabeçalho)
        //     const linha = document.querySelector(`.table.table-1 tbody tr:nth-child(${childIndex})`);

        //     if (!linha) return null;

        //     // Pega todas as células da linha
        //     const celulas = linha.querySelectorAll('td');
        //     console.log('Linha: ', celulas);
        //     return {
        //         mes: celulas[0]?.textContent.trim(),      // Janeiro/2025
        //         pis: celulas[1]?.textContent.trim(),      // 0,56%
        //         cofins: celulas[2]?.textContent.trim(),   // 2,59%
        //         total: celulas[3]?.textContent.trim()     // 3,15%
        //     };
        // });

        // if (dados) {
        //     const nomeArquivo = 'imposto.json';
        //     const dadosFormatados = {
        //         mes: dados.mes.split('/')[0],
        //         pis_pasep: dados.pis,
        //         cofins: dados.cofins,
        //         total: dados.total
        //     };

        //     fs.writeFileSync(nomeArquivo, JSON.stringify(dadosFormatados, null, 2));
        //     console.log(`Dados salvos em ${nomeArquivo}`);
        // }

        // return dados;
    } catch (error) {
        console.error('Erro ao extrair dados da tabela:', error);
        return null;
    }
}

(async () => {
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

    // const timeout = 50000;
    // page.setDefaultTimeout(timeout);

    const page = await browser.newPage();

    // Configurando viewport para mobile (exemplo de iPhone X)
    await page.setViewport({
        width: 800,
        height: 620,
        isMobile: false,
        hasTouch: false
    });

    // Navega para a página e espera carregar
    await page.goto('https://www.edp.com.br/icms-pis-e-cofins/', { waitUntil: 'networkidle2', timeout: 30000 });

    // Espera e clica no botão de aceitar cookies
    try {
        await page.waitForSelector('#onetrust-accept-btn-handler', { visible: true, timeout: 30000 });
        await page.click('#onetrust-accept-btn-handler');
        // console.log('Cookies aceitos com sucesso');

        // Verifica se o botão do ES está visível
        await page.waitForSelector('#btnESModal3', {
            visible: true,
            timeout: 30000
        });

        // Tenta clicar usando evaluate
        await page.evaluate(() => {
            const button = document.querySelector('#btnESModal3');
            button.click();
        });
        // console.log('Botão do Espírito Santo clicado com sucesso');

    } catch (error) {
        console.error('Erro durante o processo:', error);
    }

    // Clica no botão 2025
    const sucessoClique = await clicarBotao2025(page);

    // Extrai os dados
    const dados = await extrairDadosTabela(page);

    // if (dados) {
    //     console.log('Dados encontrados:');
    //     console.log('Mês:', dados.mes);
    //     console.log('PIS/PASEP:', dados.pis);
    //     console.log('COFINS:', dados.cofins);
    //     console.log('Total:', dados.total);
    // } else {
    //     console.log('Não foi possível encontrar os dados');
    // }

    await browser.close();

})().catch(error => {
    console.error('Erro durante a execução:', error);
});