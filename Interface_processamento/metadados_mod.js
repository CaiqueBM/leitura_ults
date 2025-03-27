const fs = require('fs');
const path = require('path');
const { PDFDocument } = require('pdf-lib');

async function modificarMetadatasPDF(caminhoArquivo) {
    try {
        // Verifica se o arquivo existe
        if (!fs.existsSync(caminhoArquivo)) {
            throw new Error('Arquivo não encontrado');
        }

        // Extrai o nome do arquivo do caminho e remove a extensão
        const nomeArquivo = path.basename(caminhoArquivo, '.pdf');

        // Lê o arquivo PDF
        const pdfBytes = await fs.promises.readFile(caminhoArquivo);
        
        // Carrega o PDF
        const pdfDoc = await PDFDocument.load(pdfBytes);
        
        // Define os metadados
        pdfDoc.setTitle(nomeArquivo);
        pdfDoc.setAuthor('ABS Engenharia');
        
        // Salva as alterações
        const pdfModificado = await pdfDoc.save();
        
        // Sobrescreve o arquivo original
        await fs.promises.writeFile(caminhoArquivo, pdfModificado);
        
        console.log(`Metadados do PDF atualizados com sucesso: ${caminhoArquivo}`);
        console.log(`Novo título: ${nomeArquivo}`);
    } catch (error) {
        console.error('Erro ao modificar PDF:', error);
        throw error;
    }
}

// Pega o argumento da linha de comando
// const caminhoArquivo = process.argv[2];
const caminhoArquivo = "/media/hdfs/ULT/16 - Nova apuracao/2025/Fevereiro/Pousada LUSITANIA/1419374/Dashboard/1419374-2-2025.pdf"

if (!caminhoArquivo) {
    console.error('Uso: node script.js <caminho-do-pdf>');
    process.exit(1);
}

modificarMetadatasPDF(caminhoArquivo)
    .catch(error => {
        console.error('Erro:', error);
        process.exit(1);
    });
