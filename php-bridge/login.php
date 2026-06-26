<?php
/**
 * One-time interactive login for MadelineProto.
 *
 * Run inside the Railway container shell:
 *   $ cd /usr/src/app/php-bridge && php login.php
 *
 * It will:
 *   1. Ask for your phone number (the same Telegram account as USER_SESSION_STRING)
 *   2. Send an OTP to that account (visible in your Telegram app)
 *   3. Ask for the OTP code
 *   4. Ask for your 2FA password (if you have one set)
 *   5. Save session to ./data/session.madeline
 *
 * IMPORTANT:
 *   - Mount /usr/src/app/php-bridge/data as a Railway Volume.
 *   - Without a persistent volume, the session file is wiped on every redeploy
 *     and you'll have to re-login each time.
 *
 * After this script succeeds, the server.php daemon picks up the session
 * automatically — you do NOT need to run login.php again unless you redeploy
 * without a volume, change phone number, or revoke the session from Telegram.
 */

declare(strict_types=1);

require_once __DIR__ . '/vendor/autoload.php';

use danog\MadelineProto\API;
use danog\MadelineProto\Logger;
use danog\MadelineProto\Settings;
use danog\MadelineProto\Settings\AppInfo;
use danog\MadelineProto\Settings\Logger as LoggerSettings;

$sessionDir = __DIR__ . '/data';
if (!is_dir($sessionDir)) {
    mkdir($sessionDir, 0o755, true);
}
$sessionPath = $sessionDir . '/session.madeline';

$settings = new Settings();
$appInfo = (new AppInfo())
    ->setApiId((int) (getenv('TELEGRAM_API') ?: 26676741))
    ->setApiHash(getenv('TELEGRAM_HASH') ?: '6fbc29f23c15bdb0c7fbbefe65c9193a')
    ->setDeviceModel('Zoro-Leech-PHP-Bridge')
    ->setSystemVersion('1.0')
    ->setAppVersion('1.0');
$settings->setAppInfo($appInfo);

$loggerSettings = (new LoggerSettings())
    ->setType(Logger::ECHO_LOGGER)
    ->setLevel(Logger::WARNING);
$settings->setLogger($loggerSettings);

echo "==========================================================\n";
echo "  MadelineProto Login — Zoro Leech Bot PHP Bridge\n";
echo "==========================================================\n";
echo "Session file will be saved to:\n  $sessionPath\n\n";

$MadelineProto = new API($sessionPath, $settings);
$MadelineProto->start();

$self = $MadelineProto->getSelf();
echo "\n✅ Logged in as: " . ($self['first_name'] ?? '?')
    . ' (id=' . ($self['id'] ?? '?') . ', premium=' . (isset($self['premium']) && $self['premium'] ? 'YES' : 'no') . ")\n";
echo "Session persisted. server.php will now pick it up automatically.\n";
