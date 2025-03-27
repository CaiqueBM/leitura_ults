<?php


function escreverLog($mensagem, $tipo = 'INFO') {
    // Define o diretório para os logs
    $logDir = __DIR__ . '/logs';
    
    // Cria o diretório se não existir
    if (!file_exists($logDir)) {
        mkdir($logDir, 0777, true);
    }
    
    // Define o nome do arquivo de log com a data atual
    $logFile = $logDir . '/api_' . date('Y-m-d') . '.log';
    
    // Formata a mensagem de log
    $dataHora = date('Y-m-d H:i:s');
    $logMessage = "[$dataHora][$tipo] $mensagem" . PHP_EOL;
    
    // Escreve no arquivo de log
    file_put_contents($logFile, $logMessage, FILE_APPEND);
}


// Obtém o diretório onde o script está salvo
$script_dir = dirname(__FILE__);

// Caminho correto para config.ini (subindo um nível)
$config_path = realpath($script_dir . "/../config.ini");

// Verifica se o arquivo existe
if (!$config_path || !file_exists($config_path)) {
    die("Erro: Arquivo de configuração não encontrado em $config_path");
}

// Lê o arquivo de configuração
$config = parse_ini_file($config_path, true);

// Verifica se a leitura foi bem-sucedida
if ($config === false) {
    die("Erro: Falha ao ler o arquivo de configuração");
}

// Verifica se os argumentos necessários foram passados
if (count($argv) < 5) {
    die("Uso: php auth.php <unid_consumidora> <cliente> <valor_fatura> <output>\n");
}


// Recebe os argumentos
$unid_consumidora = $argv[1];
$cliente = $argv[2];
$valor_fatura_string = $argv[3];
$valor_fatura = (float) $valor_fatura_string;
$output_file = $argv[4];

echo "\n-------------------------------------------------\n";
echo "- DADOS QUE CHEGARAM NO PHP:\n";
echo "UNIDADE CONSUMIDORA: " . $unid_consumidora . "\n";
echo "CLIENTE: " . $cliente . "\n";
echo "VALOR FATURA (STRING): " . $valor_fatura_string . "\n";
echo "VALOR FATURA (FLOAT): " . $valor_fatura . "\n";
echo "OUTPUT FILE: " . $output_file . "\n";
echo "\n-------------------------------------------------\n";

// Função para normalizar o caminho do arquivo
function normalizePath($path) {
    // Substitui as barras invertidas por barras normais
    $path = str_replace('\\', '/', $path);

    // Usa DIRECTORY_SEPARATOR para garantir compatibilidade com o sistema atual
    $path = str_replace('/', DIRECTORY_SEPARATOR, $path);

    return $path;
}

$accessToken = "";
// Diretório onde os arquivos PEM serão salvos
$directory = $config['dados']['diretorio-pasta'];
$pfxFile = $config['dados']['diretorio-pfx'];
$passphrase = $config['dados']['pass-pfx'];

// Arquivos PEM, CRT e KEY na mesma pasta
$pemFile = $directory . DIRECTORY_SEPARATOR . 'certificado_e_chave.pem';
$certificadoPem = $directory . DIRECTORY_SEPARATOR . 'certificado.pem';
$chavePrivadaPem = $directory . DIRECTORY_SEPARATOR . 'chave_privada.pem';

// Converter o PFX para PEM
$command = "openssl pkcs12 -in $pfxFile -out $pemFile -nodes -password pass:$passphrase";
exec($command, $output, $return_var);

if ($return_var !== 0) {
    echo "Erro ao converter PFX para PEM:\n";
    // print_r($output);
} else {
    echo "Conversão de PFX para PEM realizada com sucesso.\n";

    // Extrair o certificado e a chave privada do arquivo PEM
    $command = "openssl pkcs12 -in $pfxFile -clcerts -nokeys -out $certificadoPem -password pass:$passphrase";
    exec($command, $output, $return_var);

    if ($return_var !== 0) {
        echo "Erro ao extrair o certificado:\n";
        // print_r($output);
    } else {
        echo "Certificado extraído com sucesso.\n";
    }

    // Adicionar a opção -nodes para evitar a solicitação de senha
    $command = "openssl pkcs12 -in $pfxFile -nocerts -nodes -out $chavePrivadaPem -password pass:$passphrase";
    exec($command, $output, $return_var);

    if ($return_var !== 0) {
        echo "Erro ao extrair a chave privada:\n";
        // print_r($output);
    } else {
        echo "Chave privada extraída com sucesso.\n";
    }
}

$grant_type = $config['dados']['grant-type'];
$scope = $config['dados']['scope'];
$client_id = $config['dados']['client-id'];
$end_token = $config['dados']['end-token'];

// BUSCAR ACESS TOKEN
// Dados para a requisição do token
$data = http_build_query([
    'grant_type' => $grant_type,
    'client_id' => $client_id,
    'scope' => $scope,
]);

// Inicializa o cURL
$ch = curl_init();
curl_setopt_array($ch, [
    CURLOPT_URL => $end_token,
    CURLOPT_POST => true,
    CURLOPT_RETURNTRANSFER => true,
    CURLOPT_HTTPHEADER => ['Content-Type: application/x-www-form-urlencoded'],
    CURLOPT_POSTFIELDS => $data,
    CURLOPT_SSLCERT => $pemFile, // Caminho para o certificado PEM
    CURLOPT_SSLKEY => $pemFile, // Caminho para a chave privada PEM
    CURLOPT_SSLKEYPASSWD => $passphrase, // Senha da chave privada
]);

// Executa a requisição
$response = curl_exec($ch);

if ($response === false) {
    // echo 'Erro cURL: ' . curl_error($ch);
} else {
    // echo 'Resposta: ' . $response;

    // Decodificar a resposta JSON
    $responseData = json_decode($response, true);

    // Verificar se a decodificação foi bem-sucedida
    if (json_last_error() === JSON_ERROR_NONE) {
        // Armazenar o access_token em uma variável
        $accessToken = $responseData['access_token'];
        // echo "Access Token: " . $accessToken . "\n";

        // Salvar a resposta no arquivo
        // file_put_contents($responseFile, $response, FILE_APPEND);
    } else {
        echo 'Erro ao decodificar a resposta JSON: ' . json_last_error_msg();
    }
}

// Fecha a conexão cURL
curl_close($ch);


$script_dir = dirname(__FILE__);

$pastaClientes_mod = realpath($script_dir . "/../clientes");
$arquivoJson = $pastaClientes_mod . "/" . $unid_consumidora . ".json";
// echo "PATH PARA PASTA CLIENTES: " . $pastaClientes;
// $pastaClientes = 'clientes/';
// $arquivoJson = $pastaClientes . $unid_consumidora . '.json';
// $arquivoJson = $pastaClientes . $unid_consumidora . '.json';
echo $arquivoJson;

// Verifica se o arquivo JSON existe
if (!file_exists($arquivoJson)) {
    die("Arquivo JSON não encontrado: $arquivoJson");
}

// Carrega o conteúdo do arquivo JSON
$conteudoJson = file_get_contents($arquivoJson);

// Decodifica o JSON para um array associativo
$dadosJson = json_decode($conteudoJson, true);

// Verifica se o JSON é válido
if (json_last_error() !== JSON_ERROR_NONE) {
    die("Erro ao decodificar o arquivo JSON: " . json_last_error_msg());
}

$seuNumero = $unid_consumidora . '-' . date('m-y', strtotime('-1 month'));
$dataVencimento = date('Y-m') . '-20';
$dataLimitePagamento = date('Y-m') . '-30';

// Adapta os dados do JSON ao corpo da nova requisição
$newEndpointData = $dadosJson;

$newEndpointData['dataEmissao'] = (string)date('Y-m-d'); // Atualiza para a data de hoje
$newEndpointData['seuNumero'] = (string)$seuNumero;
$newEndpointData['valor'] = $valor_fatura; // Substitui o valor por algum calculado ou recebido de outra variável
$newEndpointData['dataVencimento'] = (string)$dataVencimento; // Data estática como exemplo
$newEndpointData['dataLimitePagamento'] = (string)$dataLimitePagamento; // Outra data como exemplo

// Codifica novamente o JSON para usá-lo na requisição
$newEndpointDataJson = json_encode($newEndpointData);


escreverLog("Iniciando requisição para URL: $newEndpointUrl");
escreverLog("Dados enviados: " . $newEndpointDataJson);

// Verifica se a token de autorização foi gerada com sucesso antes da nova requisição
if (empty($accessToken)) {
    die("Token de acesso não especificado. Verifique.");
}

// Prepara e faz a nova requisição cURL
$newEndpointUrl = $config['dados']['end-boleto'];


    echo "\n 00000000000000000000000000000000000000000000000000000000000000000 \n";
    echo $newEndpointDataJson;
    echo "\n 00000000000000000000000000000000000000000000000000000000000000000 \n";


    // Inicializa o cURL para a nova requisição
    $ch = curl_init();
    curl_setopt_array($ch, [
        CURLOPT_URL => $newEndpointUrl,
        CURLOPT_POST => true,
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_VERBOSE => true, // Adiciona log verboso
        CURLOPT_HEADER => true, // Retorna os headers
        CURLOPT_HTTPHEADER => [
            'Content-Type: application/json',
            'Authorization: Bearer ' . $accessToken,
            'Accept: application/json',
            'client_id:' . $client_id
        ],
        CURLOPT_POSTFIELDS => $newEndpointDataJson,
        CURLOPT_SSLCERT => $pemFile, // Caminho para o certificado PEM
        CURLOPT_SSLKEY => $pemFile, // Caminho para a chave privada PEM
        CURLOPT_SSLKEYPASSWD => $passphrase, // Senha da chave privada
    ]);

    // Executa a nova requisição
    $newResponse = curl_exec($ch);

    // Verifica se houve erro no cURL
    if (curl_errno($ch)) {
        echo 'Erro cURL: ' . curl_error($ch);
        curl_close($ch);
        exit;
}

    // Separa o header do body da resposta
    $headerSize = curl_getinfo($ch, CURLINFO_HEADER_SIZE);
    $header = substr($newResponse, 0, $headerSize);
    $body = substr($newResponse, $headerSize);

    echo "\n 00000000000000000000000000000000000000000000000000000000000000000 \n";
    echo $body;

    // Log do header e body
    escreverLog("Headers da resposta: " . $header);
    escreverLog("Body da resposta: " . $body);

    // Decodifica o JSON da resposta
    $responseData = json_decode($body, true);
    $resultado = $responseData['resultado'];
    
    echo "\n 00000000000000000000000000000000000000000000000000000000000000000 \n";
    echo $resultado;
    echo "\n 00000000000000000000000000000000000000000000000000000000000000000 \n";

    escreverLog("Dados decodificados: " . print_r($responseData, true));

    // Verifica se o JSON foi decodificado corretamente
if ($responseData === null) {
    echo 'Erro ao decodificar JSON: ' . json_last_error_msg();
    escreverLog("Erro ao decodificar JSON: $erro", 'ERRO');
    curl_close($ch);
    exit;
}

// Extrai os dados diretamente do $responseData
$codigo_barras = $resultado['codigoBarras'];
$linha_digitavel = $resultado['linhaDigitavel'];



// Fecha a conexão cURL
curl_close($ch);

// // GERAR BOLETO
// $codigo_barras = "75694999800000991441301001518627700000038001";
// $linha_digitavel = "75691301020151862770600000380014499980000099144";

// Nome do arquivo de saída
echo "\n 00000000000000000000000000000000000000000000000000000000000000000 \n";
echo $codigo_barras;
echo "\n";
echo $linha_digitavel;
echo "\n 00000000000000000000000000000000000000000000000000000000000000000 \n";

// Caminho do arquivo na mesma pasta do script
$temp_path = $script_dir . "/temp.txt";


// Abre o arquivo no modo append ('a') e escreve nele
$file = fopen($temp_path, "a");
if ($file) {
    fwrite($file,  $codigo_barras . "\n" . $linha_digitavel);
    fclose($file);
    echo "Arquivo escrito com sucesso: $temp_path";
} else {
    echo "Erro ao abrir o arquivo.";
}

echo "Dados gravados com sucesso no arquivo temporário";



?>