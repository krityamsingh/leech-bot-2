<?php
/**
 * PHP MadelineProto microservice — listens on 127.0.0.1:9090.
 *
 * The Python bot POSTs upload / download jobs here. The service uses the
 * MadelineProto user session (created via login.php once) to perform the
 * Telegram transfer with its native 20-parallel-parts default and returns
 * the result as JSON.
 *
 * Endpoints:
 *   GET  /health                      → {"ok":true,"session_id":..., "premium":bool}
 *   POST /upload   {file_path, peer, caption, as_video} → {ok, message_id, file_id, ...}
 *   POST /download {peer, message_id, save_path}        → {ok, save_path, size}
 *
 * The whole thing is single-process AMPHP — no PHP-FPM needed.
 */

declare(strict_types=1);

require_once __DIR__ . '/vendor/autoload.php';

use Amp\ByteStream;
use Amp\Http\HttpStatus;
use Amp\Http\Server\DefaultErrorHandler;
use Amp\Http\Server\Driver\SocketClientFactory;
use Amp\Http\Server\Request;
use Amp\Http\Server\RequestHandler\ClosureRequestHandler;
use Amp\Http\Server\Response;
use Amp\Http\Server\Router;
use Amp\Http\Server\SocketHttpServer;
use Amp\Socket;
use danog\MadelineProto\API;
use danog\MadelineProto\Logger;
use danog\MadelineProto\Settings;
use danog\MadelineProto\Settings\AppInfo;
use danog\MadelineProto\Settings\Logger as LoggerSettings;
use Psr\Log\NullLogger;

$sessionPath = __DIR__ . '/data/session.madeline';
if (!file_exists($sessionPath)) {
    fwrite(STDERR, "[php-bridge] ERROR: session.madeline not found at $sessionPath\n");
    fwrite(STDERR, "[php-bridge] Run `php login.php` first to create it.\n");
    exit(1);
}

$settings = new Settings();
$settings->setAppInfo(
    (new AppInfo())
        ->setApiId((int) (getenv('TELEGRAM_API') ?: 26676741))
        ->setApiHash(getenv('TELEGRAM_HASH') ?: '6fbc29f23c15bdb0c7fbbefe65c9193a')
        ->setDeviceModel('Zoro-Leech-PHP-Bridge')
        ->setAppVersion('1.0')
);
$settings->setLogger(
    (new LoggerSettings())
        ->setType(Logger::ECHO_LOGGER)
        ->setLevel(Logger::WARNING)
);

$MadelineProto = new API($sessionPath, $settings);
$MadelineProto->start();

$self = $MadelineProto->getSelf();
fwrite(STDERR, sprintf(
    "[php-bridge] Started — logged in as %s (id=%s, premium=%s)\n",
    $self['first_name'] ?? '?',
    $self['id'] ?? '?',
    !empty($self['premium']) ? 'YES' : 'no',
));

// ── helpers ──────────────────────────────────────────────────────────────────
function json_ok(array $data): Response
{
    return new Response(HttpStatus::OK, ['content-type' => 'application/json'],
        json_encode(['ok' => true] + $data, JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE));
}
function json_err(string $msg, int $code = HttpStatus::INTERNAL_SERVER_ERROR): Response
{
    return new Response($code, ['content-type' => 'application/json'],
        json_encode(['ok' => false, 'error' => $msg]));
}
function read_json(Request $req): array
{
    $raw = ByteStream\buffer($req->getBody());
    $d = json_decode($raw, true);
    return is_array($d) ? $d : [];
}

// ── handlers ─────────────────────────────────────────────────────────────────
$health = new ClosureRequestHandler(function () use ($self): Response {
    return json_ok([
        'session_id' => $self['id'] ?? null,
        'premium' => (bool) ($self['premium'] ?? false),
        'engine' => 'MadelineProto/' . API::RELEASE,
    ]);
});

$upload = new ClosureRequestHandler(function (Request $req) use ($MadelineProto): Response {
    $body = read_json($req);
    $path = $body['file_path'] ?? null;
    $peer = $body['peer'] ?? null;
    $caption = $body['caption'] ?? '';
    $asVideo = (bool) ($body['as_video'] ?? false);
    $thumb = $body['thumb'] ?? null;

    if (!$path || !$peer) {
        return json_err('missing file_path or peer', HttpStatus::BAD_REQUEST);
    }
    if (!file_exists($path)) {
        return json_err("file not found: $path", HttpStatus::NOT_FOUND);
    }
    if (!is_numeric($peer)) {
        $peer = (int) $peer;
    } else {
        $peer = (int) $peer;
    }

    try {
        $attributes = [];
        if ($asVideo) {
            $attributes[] = [
                '_' => 'documentAttributeVideo',
                'supports_streaming' => true,
            ];
        }
        $params = [
            'peer' => $peer,
            'file' => $path,
            'caption' => $caption,
            'parse_mode' => 'HTML',
            'attributes' => $attributes,
            'force_file' => !$asVideo,
        ];
        if ($thumb && file_exists($thumb)) {
            $params['thumb'] = $thumb;
        }
        $result = $MadelineProto->messages->sendMedia($params);
        $msgId = null;
        foreach ($result['updates'] ?? [] as $u) {
            if (isset($u['message']['id'])) { $msgId = $u['message']['id']; break; }
            if (isset($u['id'])) { $msgId = $u['id']; }
        }
        return json_ok(['message_id' => $msgId, 'peer' => $peer]);
    } catch (\Throwable $e) {
        return json_err($e::class . ': ' . $e->getMessage());
    }
});

$download = new ClosureRequestHandler(function (Request $req) use ($MadelineProto): Response {
    $body = read_json($req);
    $peer = $body['peer'] ?? null;
    $msgId = $body['message_id'] ?? null;
    $savePath = $body['save_path'] ?? null;
    if (!$peer || !$msgId || !$savePath) {
        return json_err('missing peer, message_id, or save_path', HttpStatus::BAD_REQUEST);
    }
    try {
        $msgs = $MadelineProto->channels->getMessages([
            'channel' => (int) $peer,
            'id' => [(int) $msgId],
        ]);
        $msg = $msgs['messages'][0] ?? null;
        if (!$msg || empty($msg['media'])) {
            return json_err('message has no media');
        }
        $dir = dirname($savePath);
        if (!is_dir($dir)) {
            mkdir($dir, 0o755, true);
        }
        $MadelineProto->downloadToFile($msg, $savePath);
        return json_ok(['save_path' => $savePath, 'size' => filesize($savePath)]);
    } catch (\Throwable $e) {
        return json_err($e::class . ': ' . $e->getMessage());
    }
});

// ── server ───────────────────────────────────────────────────────────────────
$logger = new NullLogger();
$server = SocketHttpServer::createForDirectAccess($logger);
$server->expose(new Socket\InternetAddress('127.0.0.1', 9090));
$router = new Router($server, $logger, new DefaultErrorHandler());
$router->addRoute('GET', '/health', $health);
$router->addRoute('POST', '/upload', $upload);
$router->addRoute('POST', '/download', $download);
$server->start($router, new DefaultErrorHandler());

fwrite(STDERR, "[php-bridge] Listening on http://127.0.0.1:9090\n");

// Keep alive
$signal = Amp\trapSignal([SIGINT, SIGTERM]);
fwrite(STDERR, "[php-bridge] Received signal $signal, shutting down\n");
$server->stop();
$MadelineProto->stop();
