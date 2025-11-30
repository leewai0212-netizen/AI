<?php
session_start();

$dataFile = __DIR__ . '/card_keys.json';
$devicesFile = __DIR__ . '/devices.json';
$accountsFile = __DIR__ . '/accounts.json';
$logsFile = __DIR__ . '/system_logs.json';
$notificationsFile = __DIR__ . '/notifications.json';
$configFile = __DIR__ . '/system_config.json';
$backupsDir = __DIR__ . '/backups/';
$applicationsFile = __DIR__ . '/applications.json';
$cardPointsFile = __DIR__ . '/card_points_config.json';
$trialSessionsFile = __DIR__ . '/trial_sessions.json';

const DEVICE_TIMEOUT_SECONDS = 18000; // 5 hours

function readJsonFile(string $path, $default = []) {
    if (!file_exists($path)) {
        return $default;
    }
    $content = file_get_contents($path);
    if ($content === false || $content === '') {
        return $default;
    }
    $decoded = json_decode($content, true);
    return is_array($decoded) ? $decoded : $default;
}

function writeJsonFile(string $path, $data): void {
    file_put_contents($path, json_encode($data, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE));
}

function functionAvailable(string $name): bool {
    if (!function_exists($name)) {
        return false;
    }
    $disabled = ini_get('disable_functions') ?: '';
    $disabledList = array_map('trim', explode(',', $disabled));
    return !in_array($name, $disabledList, true);
}

function pathAllowedByOpenBaseDir(string $path): bool {
    $restrictions = ini_get('open_basedir');
    if (!$restrictions) {
        return true;
    }
    $normalized = rtrim($path, '/');
    foreach (explode(PATH_SEPARATOR, $restrictions) as $allowed) {
        $allowed = rtrim($allowed, '/');
        if ($allowed === '') {
            continue;
        }
        if (strncmp($normalized, $allowed, strlen($allowed)) === 0) {
            return true;
        }
    }
    return false;
}

function readSystemFile(string $path): ?string {
    if (pathAllowedByOpenBaseDir($path)) {
        $content = @file_get_contents($path);
        if ($content !== false) {
            $trimmed = trim($content);
            if ($trimmed !== '') {
                return $trimmed;
            }
        }
    }
    if (functionAvailable('shell_exec')) {
        $output = @shell_exec('cat ' . escapeshellarg($path) . ' 2>/dev/null');
        if (is_string($output)) {
            $trimmed = trim($output);
            if ($trimmed !== '') {
                return $trimmed;
            }
        }
    }
    return null;
}

function readSystemCommand(string $command): ?string {
    if (!functionAvailable('shell_exec')) {
        return null;
    }
    $output = @shell_exec($command . ' 2>/dev/null');
    if (is_string($output)) {
        $trimmed = trim($output);
        if ($trimmed !== '') {
            return $trimmed;
        }
    }
    return null;
}

function initSystemConfig(): void {
    global $configFile;
    if (!file_exists($configFile)) {
        $default = [
            'security' => [
                'ip_whitelist' => [],
                'ip_blacklist' => [],
                'jwt_secret' => 'please-change-me-' . bin2hex(random_bytes(8)),
                'session_timeout' => 3600
            ],
            'backup' => [
                'auto_backup' => true,
                'backup_interval' => 86400,
                'keep_days' => 15
            ],
            'monitoring' => [
                'enable_alerts' => true,
                'max_cpu_usage' => 80,
                'max_memory_usage' => 80,
                'max_disk_usage' => 90
            ],
            'card_groups' => [
                'normal' => ['name' => '默认分组', 'color' => '#4CAF50'],
                'vip' => ['name' => 'VIP', 'color' => '#F39C12'],
                'trial' => ['name' => '试用', 'color' => '#2196F3']
            ],
            'trial' => [
                'duration_seconds' => 3600
            ]
        ];
        writeJsonFile($configFile, $default);
    }
}

function getSystemConfig(): array {
    global $configFile;
    return readJsonFile($configFile, []);
}

function updateSystemConfig(array $config): void {
    global $configFile;
    writeJsonFile($configFile, $config);
}

function addLog(string $action, string $userId, array $details = []): void {
    global $logsFile;
    $logs = readLogs();
    $logs[] = [
        'id' => uniqid('log_', true),
        'action' => $action,
        'user_id' => $userId,
        'user_type' => $_SESSION['user_type'] ?? 'system',
        'username' => $_SESSION['username'] ?? 'system',
        'ip' => $_SERVER['REMOTE_ADDR'] ?? '0.0.0.0',
        'user_agent' => $_SERVER['HTTP_USER_AGENT'] ?? '',
        'details' => $details,
        'created_at' => date('Y-m-d H:i:s')
    ];
    writeLogs($logs);
}

function readLogs(): array {
    global $logsFile;
    return readJsonFile($logsFile, []);
}

function writeLogs(array $logs): void {
    global $logsFile;
    if (count($logs) > 500) {
        $logs = array_slice($logs, -500);
    }
    writeJsonFile($logsFile, $logs);
}

function readNotifications(): array {
    global $notificationsFile;
    return readJsonFile($notificationsFile, []);
}

function writeNotifications(array $notifications): void {
    global $notificationsFile;
    if (count($notifications) > 100) {
        $notifications = array_slice($notifications, -100);
    }
    writeJsonFile($notificationsFile, $notifications);
}

function checkIPAccess(string $ip): bool {
    $config = getSystemConfig();
    $allowed = $config['security']['ip_whitelist'] ?? [];
    $blocked = $config['security']['ip_blacklist'] ?? [];

    if (in_array($ip, $blocked, true)) {
        return false;
    }

    if (!empty($allowed)) {
        foreach ($allowed as $range) {
            if (strpos($range, '/') !== false) {
                if (ip_in_subnet($ip, $range)) {
                    return true;
                }
            } elseif ($ip === $range) {
                return true;
            }
        }
        return false;
    }

    return true;
}

function ip_in_subnet(string $ip, string $subnet): bool {
    if (strpos($subnet, '/') === false) {
        return $ip === $subnet;
    }
    [$subnetIp, $mask] = explode('/', $subnet);
    $mask = (int) $mask;
    if ($mask < 0 || $mask > 32) {
        return false;
    }
    $ipLong = ip2long($ip);
    $subnetLong = ip2long($subnetIp);
    if ($ipLong === false || $subnetLong === false) {
        return false;
    }
    $maskLong = -1 << (32 - $mask);
    return ($ipLong & $maskLong) === ($subnetLong & $maskLong);
}

function generateJWT(string $userId, string $role): string {
    $config = getSystemConfig();
    $secret = $config['security']['jwt_secret'] ?? 'fallback-secret';
    $header = base64_encode(json_encode(['alg' => 'HS256', 'typ' => 'JWT']));
    $payload = base64_encode(json_encode([
        'user_id' => $userId,
        'role' => $role,
        'iat' => time(),
        'exp' => time() + 3600
    ]));
    $signature = hash_hmac('sha256', $header . '.' . $payload, $secret, true);
    return str_replace('=', '', strtr($header, '+/', '-_')) . '.' .
        str_replace('=', '', strtr($payload, '+/', '-_')) . '.' .
        str_replace('=', '', strtr(base64_encode($signature), '+/', '-_'));
}

function verifyJWT(string $jwt) {
    $parts = explode('.', $jwt);
    if (count($parts) !== 3) {
        return false;
    }
    $config = getSystemConfig();
    $secret = $config['security']['jwt_secret'] ?? 'fallback-secret';
    [$header, $payload, $signature] = $parts;
    $expected = hash_hmac('sha256', $header . '.' . $payload, $secret, true);
    $expectedEncoded = str_replace('=', '', strtr(base64_encode($expected), '+/', '-_'));
    if (!hash_equals($expectedEncoded, $signature)) {
        return false;
    }
    $payloadObj = json_decode(base64_decode(strtr($payload, '-_', '+/')), true);
    if (!$payloadObj || ($payloadObj['exp'] ?? 0) < time()) {
        return false;
    }
    return $payloadObj;
}

function getSystemStatus(): array {
    $load = function_exists('sys_getloadavg') ? sys_getloadavg() : [0];
    $cpuCores = getCpuCoreCount();
    $cpu = '受限';
    if ($cpuCores > 0 && isset($load[0])) {
        $cpu = round(min(100, ($load[0] / max(1, $cpuCores)) * 100), 1);
    } else {
        $loadAvgText = readSystemFile('/proc/loadavg') ?? readSystemCommand('cat /proc/loadavg');
        if ($loadAvgText) {
            $parts = preg_split('/\s+/', trim($loadAvgText));
            $loadValue = (float) ($parts[0] ?? 0);
            if ($cpuCores > 0 && $loadValue >= 0) {
                $cpu = round(min(100, ($loadValue / max(1, $cpuCores)) * 100), 1);
            }
        }
    }
    $memoryUsage = '受限';
    $memInfo = readSystemFile('/proc/meminfo');
    if ($memInfo !== null) {
        $memTotal = null;
        $memAvailable = null;
        foreach (explode("\n", $memInfo) as $line) {
            if (strpos($line, 'MemTotal:') === 0) {
                $memTotal = (int) filter_var($line, FILTER_SANITIZE_NUMBER_INT);
            } elseif (strpos($line, 'MemAvailable:') === 0) {
                $memAvailable = (int) filter_var($line, FILTER_SANITIZE_NUMBER_INT);
            }
            if ($memTotal !== null && $memAvailable !== null) {
                break;
            }
        }
        if ($memTotal !== null && $memAvailable !== null && $memTotal > 0) {
            $usedKb = max(0, $memTotal - $memAvailable);
            $memoryUsage = round($usedKb / 1024, 2); // MB
        }
    } else {
        $freeOutput = readSystemCommand('free -k');
        if ($freeOutput) {
            $lines = preg_split('/\r?\n/', $freeOutput);
            foreach ($lines as $line) {
                $line = trim($line);
                if (stripos($line, 'Mem:') === 0) {
                    $pieces = preg_split('/\s+/', $line);
                    if (count($pieces) >= 3) {
                        $usedKb = (int) ($pieces[2] ?? 0);
                        if ($usedKb > 0) {
                            $memoryUsage = round($usedKb / 1024, 2);
                        }
                    }
                    break;
                }
            }
        }
    }
    if (!is_numeric($memoryUsage)) {
        $memoryUsage = round(memory_get_usage(true) / 1048576, 2);
    }
    $diskUsage = 0;
    if (function_exists('disk_free_space')) {
        $total = @disk_total_space('/');
        $free = @disk_free_space('/');
        if ($total > 0 && $free >= 0) {
            $diskUsage = round((1 - ($free / $total)) * 100, 2);
        }
    }
    return [
        'cpu_usage' => $cpu,
        'memory_usage' => $memoryUsage,
        'disk_usage' => $diskUsage,
        'active_connections' => countActiveConnections(),
        'api_calls_today' => getAPICallsToday(),
        'error_count_today' => getErrorCountToday(),
        'uptime' => getUptime()
    ];
}

function countActiveConnections(): int {
    $devices = readDevices();
    $count = 0;
    foreach ($devices as $cardDevices) {
        if (!is_array($cardDevices)) {
            continue;
        }
        foreach ($cardDevices as $device) {
            if (($device['status'] ?? 'online') === 'kicked') {
                continue;
            }
            $last = isset($device['last_heartbeat']) ? strtotime($device['last_heartbeat']) : 0;
            if ($last && (time() - $last) <= 300) {
                $count++;
            }
        }
    }
    return $count;
}

function getAPICallsToday(): int {
    $logs = readLogs();
    $today = date('Y-m-d');
    $count = 0;
    foreach ($logs as $log) {
        if (strpos($log['action'] ?? '', 'api_') === 0 && isset($log['created_at'])) {
            if (substr($log['created_at'], 0, 10) === $today) {
                $count++;
            }
        }
    }
    return $count;
}

function getErrorCountToday(): int {
    $logs = readLogs();
    $today = date('Y-m-d');
    $count = 0;
    foreach ($logs as $log) {
        if (strpos($log['action'] ?? '', 'error') === 0 && isset($log['created_at'])) {
            if (substr($log['created_at'], 0, 10) === $today) {
                $count++;
            }
        }
    }
    return $count;
}

function getUptime(): string {
    $contents = readSystemFile('/proc/uptime');
    if ($contents !== null) {
        $parts = explode(' ', $contents);
        $secondsFloat = (float) ($parts[0] ?? 0);
        $seconds = (int) floor($secondsFloat);
        if ($seconds < 0) {
            $seconds = 0;
        }
        $days = intdiv($seconds, 86400);
        $hours = intdiv($seconds % 86400, 3600);
        $minutes = intdiv($seconds % 3600, 60);
        return sprintf('%d天 %d小时 %d分钟', $days, $hours, $minutes);
    }
    $uptimePretty = readSystemCommand('uptime -p');
    if ($uptimePretty !== null) {
        return str_replace('up ', '', $uptimePretty);
    }
    $uptimeRaw = readSystemCommand('cat /proc/uptime');
    if ($uptimeRaw !== null) {
        $parts = explode(' ', $uptimeRaw);
        $secondsFloat = (float) ($parts[0] ?? 0);
        $seconds = (int) floor($secondsFloat);
        if ($seconds < 0) {
            $seconds = 0;
        }
        $days = intdiv($seconds, 86400);
        $hours = intdiv($seconds % 86400, 3600);
        $minutes = intdiv($seconds % 3600, 60);
        return sprintf('%d天 %d小时 %d分钟', $days, $hours, $minutes);
    }
    return '未知';
}

function getCpuCoreCount(): int {
    static $count = null;
    if ($count !== null) {
        return $count;
    }
    if (functionAvailable('shell_exec')) {
        $nproc = trim((string) @shell_exec('nproc 2>/dev/null'));
        if (ctype_digit($nproc) && (int) $nproc > 0) {
            return $count = (int) $nproc;
        }
    }
    $cpuinfo = readSystemFile('/proc/cpuinfo');
    if ($cpuinfo !== null) {
        $matches = substr_count($cpuinfo, 'processor');
        if ($matches > 0) {
            return $count = $matches;
        }
    }
    return $count = 1;
}

function autoBackup(): void {
    global $backupsDir, $dataFile, $devicesFile, $accountsFile, $logsFile;
    if (!is_dir($backupsDir)) {
        mkdir($backupsDir, 0755, true);
    }
    $timestamp = date('Y-m-d_H-i-s');
    $target = $backupsDir . $timestamp;
    if (!mkdir($target, 0755, true) && !is_dir($target)) {
        return;
    }
    foreach ([
        $dataFile => 'card_keys.json',
        $devicesFile => 'devices.json',
        $accountsFile => 'accounts.json',
        $logsFile => 'system_logs.json'
    ] as $source => $name) {
        if (file_exists($source)) {
            copy($source, $target . '/' . $name);
        }
    }
    writeJsonFile($target . '/backup_info.json', [
        'created_at' => date('Y-m-d H:i:s'),
        'system_status' => getSystemStatus()
    ]);
    cleanOldBackups();
    addLog('system_backup', 'system', ['dir' => $target]);
}

function cleanOldBackups(): void {
    global $backupsDir;
    $config = getSystemConfig();
    $keepDays = max(1, (int) ($config['backup']['keep_days'] ?? 7));
    if (!is_dir($backupsDir)) {
        return;
    }
    $entries = glob($backupsDir . '*', GLOB_ONLYDIR);
    foreach ($entries as $dir) {
        $created = strtotime(basename($dir));
        if ($created && (time() - $created) > $keepDays * 86400) {
            deleteDirectory($dir);
        }
    }
}

function deleteDirectory(string $dir): void {
    if (!is_dir($dir)) {
        return;
    }
    $items = array_diff(scandir($dir), ['.', '..']);
    foreach ($items as $item) {
        $path = $dir . '/' . $item;
        if (is_dir($path)) {
            deleteDirectory($path);
        } else {
            unlink($path);
        }
    }
    rmdir($dir);
}

$cardTypes = [
    'hour' => ['name' => '小时卡', 'color' => '#FF6B6B', 'duration' => 3600, 'points' => 1],
    'day' => ['name' => '天卡', 'color' => '#4ECDC4', 'duration' => 86400, 'points' => 5],
    'month' => ['name' => '月卡', 'color' => '#45B7D1', 'duration' => 2592000, 'points' => 50],
    'quarter' => ['name' => '季卡', 'color' => '#96CEB4', 'duration' => 7776000, 'points' => 120],
    'year' => ['name' => '年卡', 'color' => '#DDA0DD', 'duration' => 31536000, 'points' => 400],
    'permanent' => ['name' => '永久卡', 'color' => '#FFD700', 'duration' => 0, 'points' => 1000]
];

function getCardTypesWithDynamicPoints(): array {
    global $cardTypes, $cardPointsFile;
    $config = readJsonFile($cardPointsFile, []);
    $types = $cardTypes;
    foreach ($config as $type => $points) {
        if (isset($types[$type])) {
            $types[$type]['points'] = (int) $points;
        }
    }
    return $types;
}

function isLoggedIn(): bool {
    return isset($_SESSION['user_type'], $_SESSION['username']);
}

function isAdmin(): bool {
    return isLoggedIn() && $_SESSION['user_type'] === 'admin';
}

function isAgent(): bool {
    return isLoggedIn() && $_SESSION['user_type'] === 'agent';
}

function manageDevice(string $cardKey, string $deviceId, string $deviceInfo, int $maxDevices): array {
    $devices = readDevices();
    if (!isset($devices[$cardKey]) || !is_array($devices[$cardKey])) {
        $devices[$cardKey] = [];
    }
    $cardDevices = $devices[$cardKey];

    $now = time();
    $cardDevices = array_filter($cardDevices, function ($device) use ($now) {
        if (($device['status'] ?? 'online') === 'kicked') {
            $kickedAt = isset($device['kicked_time']) ? strtotime($device['kicked_time']) : 0;
            return $kickedAt && ($now - $kickedAt) < 300;
        }
        return true;
    });
    $cardDevices = array_values($cardDevices);

    $onlineDevices = [];
    $kickedDevices = [];
    foreach ($cardDevices as $device) {
        if (($device['status'] ?? 'online') === 'kicked') {
            $kickedDevices[] = $device;
        } else {
            $onlineDevices[] = $device;
        }
    }

    $deviceIndex = null;
    foreach ($onlineDevices as $idx => $device) {
        if ($device['device_id'] === $deviceId) {
            $deviceIndex = $idx;
            break;
        }
    }

    $kicked = null;
    if ($deviceIndex === null && count($onlineDevices) >= $maxDevices) {
        usort($onlineDevices, function ($a, $b) {
            return strtotime($a['last_heartbeat']) <=> strtotime($b['last_heartbeat']);
        });
        $kicked = array_shift($onlineDevices);
        $kicked['status'] = 'kicked';
        $kicked['kicked_time'] = date('Y-m-d H:i:s');
        $kicked['kicked_reason'] = '设备数量超限';
        $kickedDevices[] = $kicked;
        addLog('device_kicked', $_SESSION['user_id'] ?? 'system', [
            'card_key' => $cardKey,
            'device_id' => $kicked['device_id']
        ]);
    }

    if ($deviceIndex === null) {
        $onlineDevices[] = [
            'device_id' => $deviceId,
            'device_info' => $deviceInfo,
            'login_time' => date('Y-m-d H:i:s'),
            'last_heartbeat' => date('Y-m-d H:i:s'),
            'ip' => $_SERVER['REMOTE_ADDR'] ?? '0.0.0.0',
            'status' => 'online'
        ];
    } else {
        $onlineDevices[$deviceIndex]['last_heartbeat'] = date('Y-m-d H:i:s');
        $onlineDevices[$deviceIndex]['device_info'] = $deviceInfo;
        $onlineDevices[$deviceIndex]['ip'] = $_SERVER['REMOTE_ADDR'] ?? '0.0.0.0';
    }

    $devices[$cardKey] = array_merge($onlineDevices, $kickedDevices);
    writeDevices($devices);

    return [
        'devices' => $devices[$cardKey],
        'is_new_device' => $deviceIndex === null,
        'kicked_device' => $kicked,
        'online_count' => count($onlineDevices)
    ];
}

function initDatabase(): void {
    global $dataFile, $devicesFile, $accountsFile;
    foreach ([
        $dataFile => [],
        $devicesFile => [],
        $accountsFile => [[
            'id' => 'agent_default',
            'username' => 'demo_agent',
            'password' => 'demo123',
            'type' => 'agent',
            'points' => 1000,
            'created_at' => date('Y-m-d H:i:s')
        ]]
    ] as $file => $default) {
        if (!file_exists($file)) {
            writeJsonFile($file, $default);
        }
    }
}

function readData(): array {
    global $dataFile;
    return readJsonFile($dataFile, []);
}

function writeData(array $data): void {
    global $dataFile;
    writeJsonFile($dataFile, $data);
}

function enforceDeviceTimeouts(array $devices, int $timeoutSeconds = DEVICE_TIMEOUT_SECONDS): array {
    $changed = false;
    $now = time();
    foreach ($devices as $cardKey => &$cardDevices) {
        if (!is_array($cardDevices)) {
            continue;
        }
        foreach ($cardDevices as &$device) {
            $status = $device['status'] ?? 'online';
            $heartbeatSource = $device['last_heartbeat'] ?? ($device['login_time'] ?? null);
            $lastHeartbeat = $heartbeatSource ? strtotime($heartbeatSource) : 0;
            if ($status !== 'kicked') {
                if (!$lastHeartbeat || ($now - $lastHeartbeat) >= $timeoutSeconds) {
                    $device['status'] = 'kicked';
                    $device['kicked_time'] = date('Y-m-d H:i:s', $now);
                    $device['kicked_reason'] = '长时间无心跳';
                    $changed = true;
                }
            }
        }
        unset($device);
        $cardDevices = array_values($cardDevices);
    }
    unset($cardDevices);
    return ['devices' => $devices, 'changed' => $changed];
}

function readDevices(): array {
    global $devicesFile;
    $devices = readJsonFile($devicesFile, []);
    $result = enforceDeviceTimeouts($devices);
    if ($result['changed']) {
        writeJsonFile($devicesFile, $result['devices']);
    }
    return $result['devices'];
}

function writeDevices(array $devices): void {
    global $devicesFile;
    writeJsonFile($devicesFile, $devices);
}

function readAccounts(): array {
    global $accountsFile;
    return readJsonFile($accountsFile, []);
}

function writeAccounts(array $accounts): void {
    global $accountsFile;
    writeJsonFile($accountsFile, $accounts);
}

function createDefaultApplication(string $id = 'app_general', string $name = '通用', string $description = '默认应用'): array {
    return [
        'id' => $id,
        'name' => $name,
        'description' => $description
    ];
}

function readApplications(): array {
    global $applicationsFile;
    $apps = readJsonFile($applicationsFile, []);
    $changed = false;

    if (empty($apps)) {
        $apps = [createDefaultApplication()];
        $changed = true;
    }

    $hasGeneral = false;
    foreach ($apps as $app) {
        if (($app['id'] ?? '') === 'app_general') {
            $hasGeneral = true;
            break;
        }
    }
    if (!$hasGeneral) {
        $apps[] = createDefaultApplication();
        $changed = true;
    }

    foreach ($apps as &$app) {
        if (empty($app['id'])) {
            $app['id'] = 'app_' . substr(bin2hex(random_bytes(4)), 0, 6);
            $changed = true;
        }
        if (empty($app['name'])) {
            $app['name'] = $app['id'];
            $changed = true;
        }
        if (!isset($app['description'])) {
            $app['description'] = '';
            $changed = true;
        }
        unset($app['app_key'], $app['app_secret'], $app['rate_limit_per_min']);
    }
    unset($app);

    if ($changed) {
        writeApplications($apps);
    }

    return $apps;
}

function writeApplications(array $applications): void {
    global $applicationsFile;
    writeJsonFile($applicationsFile, array_values($applications));
}

function readTrialSessions(): array {
    global $trialSessionsFile;
    return readJsonFile($trialSessionsFile, []);
}

function writeTrialSessions(array $sessions): void {
    global $trialSessionsFile;
    writeJsonFile($trialSessionsFile, $sessions);
}

function getTrialDurationSeconds(): int {
    $config = getSystemConfig();
    return max(60, (int) ($config['trial']['duration_seconds'] ?? 3600));
}

function generateCardKey(int $length = 8): string {
    $pool = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789';
    $max = strlen($pool) - 1;
    $key = '';
    for ($i = 0; $i < $length; $i++) {
        $key .= $pool[random_int(0, $max)];
    }
    return $key;
}

function filterCardsForAgent(array $cards, string $agentName, string $agentId, string $appScope = 'all'): array {
    return array_values(array_filter($cards, function ($card) use ($agentName, $agentId, $appScope) {
        $cardApp = $card['app_id'] ?? 'app_general';
        $matchesScope = $appScope === 'all' || $cardApp === $appScope || $cardApp === 'app_general';
        if (($card['agent_id'] ?? '') === $agentId) {
            return $matchesScope;
        }
        if (($card['created_by'] ?? '') === $agentId) {
            return $matchesScope;
        }
        $notes = $card['notes'] ?? '';
        $belongs = strpos($notes, '代理生成: ' . $agentName) !== false ||
            strpos($notes, '代理提卡: ' . $agentName) !== false;
        if (!$belongs) {
            return false;
        }
        return $appScope === 'all' || ($card['app_id'] ?? 'app_general') === $appScope;
    }));
}

function cardVisibleToCurrentUser(array $card): bool {
    if (isAdmin()) {
        return true;
    }
    if (isAgent()) {
        $agentId = $_SESSION['user_id'] ?? '';
        $agentName = $_SESSION['username'] ?? '';
        $appScope = $_SESSION['agent_app_id'] ?? 'all';
        return filterCardsForAgent([$card], $agentName, $agentId, $appScope) !== [];
    }
    return false;
}

function adjustCardExpireDays(array $card, int $days, array $cardTypes): array {
    if ($days === 0) {
        return $card;
    }
    $seconds = $days * 86400;
    if (!empty($card['expire_time'])) {
        $timestamp = strtotime($card['expire_time']) + $seconds;
        $card['expire_time'] = $timestamp > 0 ? date('Y-m-d H:i:s', $timestamp) : null;
    } elseif ($days > 0) {
        $base = time();
        if (($cardTypes[$card['type']]['duration'] ?? 0) > 0) {
            $base = time() + ($cardTypes[$card['type']]['duration']);
        }
        $card['expire_time'] = date('Y-m-d H:i:s', $base + $seconds);
    }
    return $card;
}

function getCardOwnerLabel(array $card, array $userLookup): string {
    $creatorId = $card['created_by'] ?? '';
    if ($creatorId && isset($userLookup[$creatorId])) {
        return $userLookup[$creatorId];
    }
    if (!empty($card['notes'])) {
        return $card['notes'];
    }
    return '未知';
}

function changeAgentPoints(string $agentId, int $delta, ?string &$error = null): bool {
    if ($agentId === '' || $agentId === 'admin') {
        return true;
    }
    $accounts = readAccounts();
    foreach ($accounts as &$account) {
        if (($account['id'] ?? '') === $agentId && ($account['type'] ?? '') === 'agent') {
            $current = $account['points'] ?? 0;
            if ($delta < 0 && $current < abs($delta)) {
                $error = '积分不足';
                return false;
            }
            $account['points'] = $current + $delta;
            writeAccounts($accounts);
            return true;
        }
    }
    $error = '代理不存在';
    return false;
}

function calculatePointsDeltaForDays(array $card, int $days): int {
    global $cardTypes;
    $type = $card['type'] ?? '';
    if (!isset($cardTypes[$type])) {
        return 0;
    }
    $durationSeconds = $cardTypes[$type]['duration'] ?? 0;
    $basePoints = $cardTypes[$type]['points'] ?? 0;
    if ($durationSeconds <= 0 || $basePoints <= 0) {
        return 0;
    }
    $pointsPerSecond = $basePoints / $durationSeconds;
    $deltaSeconds = $days * 86400;
    return (int) round($pointsPerSecond * $deltaSeconds);
}

function cardMatchesApp(array $card, string $requestedApp): bool {
    return true;
}

initSystemConfig();
initDatabase();

$applications = readApplications();
$applicationsById = [];
foreach ($applications as $app) {
    if (!isset($app['id'])) {
        continue;
    }
    $applicationsById[$app['id']] = $app;
}
if (!isset($applicationsById['app_general'])) {
    $defaultApp = createDefaultApplication();
    $applicationsById['app_general'] = $defaultApp;
    $applications[] = $defaultApp;
    writeApplications($applications);
}

$clientIP = $_SERVER['REMOTE_ADDR'] ?? '0.0.0.0';
if (!checkIPAccess($clientIP)) {
    http_response_code(403);
    echo json_encode(['error' => 'IP访问被拒绝'], JSON_UNESCAPED_UNICODE);
    addLog('ip_blocked', 'system', ['ip' => $clientIP]);
    exit;
}

$config = getSystemConfig();
$cardTypes = getCardTypesWithDynamicPoints();

if (isset($_GET['api'])) {
    header('Content-Type: application/json');
    header('Access-Control-Allow-Origin: *');
    header('Access-Control-Allow-Methods: GET, POST, OPTIONS');
    header('Access-Control-Allow-Headers: Content-Type, Authorization');

    if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
        http_response_code(204);
        exit;
    }

    $action = $_GET['api'];
    $rawInput = file_get_contents('php://input');
    if ($rawInput === false) {
        $rawInput = '';
    }
    $payload = json_decode($rawInput, true);
    if (!is_array($payload)) {
        $payload = $_POST ?? [];
        if ($rawInput === '' && !empty($payload)) {
            $rawInput = json_encode($payload, JSON_UNESCAPED_UNICODE);
        }
    }

    $accounts = readAccounts();
    $data = readData();

    $jwtHeader = $_SERVER['HTTP_AUTHORIZATION'] ?? '';
    if ($jwtHeader && stripos($jwtHeader, 'Bearer ') === 0) {
        $jwt = substr($jwtHeader, 7);
        if (!verifyJWT($jwt)) {
            http_response_code(401);
            echo json_encode(['error' => '无效令牌'], JSON_UNESCAPED_UNICODE);
            exit;
        }
    }

    $response = ['code' => 400, 'message' => '未知接口'];

    $requestedApp = $payload['app_id'] ?? ($_GET['app_id'] ?? 'app_general');
    if (!isset($applicationsById[$requestedApp])) {
        $requestedApp = 'app_general';
    }

    $cardByKey = [];
    foreach ($data as $card) {
        $cardByKey[$card['card_key']] = $card;
    }

    $cardKey = $payload['card_key'] ?? '';
    $deviceId = $payload['device_id'] ?? '';

    switch ($action) {
        case 'verify':
            if (!$cardKey || !$deviceId) {
                $response = ['code' => 401, 'message' => '参数不完整'];
                break;
            }
            if (!isset($cardByKey[$cardKey])) {
                $response = ['code' => 402, 'message' => '卡密不存在'];
                break;
            }
            $card = $cardByKey[$cardKey];
            if (($card['disabled'] ?? false)) {
                $response = ['code' => 403, 'message' => '卡密已禁用'];
                break;
            }
            if ($card['status'] === 'unused') {
                foreach ($data as &$item) {
                    if ($item['card_key'] === $cardKey) {
                        $item['status'] = 'used';
                        $item['used_at'] = date('Y-m-d H:i:s');
                        $duration = $cardTypes[$item['type']]['duration'] ?? 0;
                        $item['expire_time'] = $duration > 0 ? date('Y-m-d H:i:s', time() + $duration) : null;
                        $item['used_by'] = $payload['device_info'] ?? '';
                        $card = $item;
                        break;
                    }
                }
                writeData($data);
            }
            if (!empty($card['expire_time']) && strtotime($card['expire_time']) < time()) {
                $response = ['code' => 405, 'message' => '卡密已过期'];
                break;
            }
            $maxDevices = $card['max_devices'] ?? 1;
            $result = manageDevice($cardKey, $deviceId, $payload['device_info'] ?? '', $maxDevices);
            $response = [
                'code' => 200,
                'message' => $result['is_new_device'] ? '设备登录成功' : '设备验证成功',
                'data' => [
                    'card_type' => $card['type'],
                    'card_name' => $cardTypes[$card['type']]['name'] ?? $card['type'],
                    'expire_time' => $card['expire_time'],
                    'max_devices' => $maxDevices,
                    'app_id' => $card['app_id'] ?? 'app_general',
                    'online_count' => $result['online_count'],
                    'kicked_device' => $result['kicked_device']
                ]
            ];
            break;
        case 'login':
            if (!$cardKey || !$deviceId) {
                $response = ['code' => 401, 'message' => '参数不完整'];
                break;
            }
            if (!isset($cardByKey[$cardKey])) {
                $response = ['code' => 402, 'message' => '卡密不存在'];
                break;
            }
            $card = $cardByKey[$cardKey];
            if ($card['status'] === 'unused') {
                foreach ($data as &$item) {
                    if ($item['card_key'] === $cardKey) {
                        $item['status'] = 'used';
                        $item['used_at'] = date('Y-m-d H:i:s');
                        $duration = $cardTypes[$item['type']]['duration'] ?? 0;
                        $item['expire_time'] = $duration > 0 ? date('Y-m-d H:i:s', time() + $duration) : null;
                        $item['used_by'] = $payload['device_info'] ?? '';
                        $card = $item;
                        break;
                    }
                }
                writeData($data);
            }
            if (($card['disabled'] ?? false)) {
                $response = ['code' => 403, 'message' => '卡密无效'];
                break;
            }
            if (!empty($card['expire_time']) && strtotime($card['expire_time']) < time()) {
                $response = ['code' => 405, 'message' => '卡密已过期'];
                break;
            }
            $maxDevices = $card['max_devices'] ?? 1;
            $result = manageDevice($cardKey, $deviceId, $payload['device_info'] ?? '', $maxDevices);
            $response = [
                'code' => 200,
                'message' => $result['is_new_device'] ? '设备登录成功' : '设备重新登录成功',
                'data' => [
                    'card_type' => $card['type'],
                    'card_name' => $cardTypes[$card['type']]['name'] ?? $card['type'],
                    'expire_time' => $card['expire_time'],
                    'online_count' => $result['online_count'],
                    'app_id' => $card['app_id'] ?? 'app_general',
                    'kicked_device' => $result['kicked_device']
                ]
            ];
            break;
        case 'heartbeat':
            if (!$cardKey || !$deviceId) {
                $response = ['code' => 401, 'message' => '参数不完整'];
                break;
            }
            $devices = readDevices();
            $cardDevices = $devices[$cardKey] ?? [];
            $found = false;
            foreach ($cardDevices as &$device) {
                if ($device['device_id'] === $deviceId) {
                    if (($device['status'] ?? 'online') === 'kicked') {
                        $response = ['code' => 407, 'message' => '设备已被踢掉'];
                    } else {
                        $device['last_heartbeat'] = date('Y-m-d H:i:s');
                        $device['ip'] = $_SERVER['REMOTE_ADDR'] ?? '0.0.0.0';
                        $response = ['code' => 200, 'message' => '心跳成功'];
                    }
                    $found = true;
                    break;
                }
            }
            if (!$found) {
                $response = ['code' => 406, 'message' => '设备未登录'];
            } else {
                $devices[$cardKey] = $cardDevices;
                writeDevices($devices);
            }
            break;
        case 'logout':
            $devices = readDevices();
            if (isset($devices[$cardKey])) {
                $devices[$cardKey] = array_values(array_filter($devices[$cardKey], function ($device) use ($deviceId) {
                    return $device['device_id'] !== $deviceId;
                }));
                writeDevices($devices);
            }
            $response = ['code' => 200, 'message' => '退出成功'];
            break;
        case 'trial':
            $trialDevice = trim($payload['device_id'] ?? '');
            $requestedDuration = (int) ($payload['duration'] ?? 0);
            $trialDuration = $requestedDuration > 0 ? $requestedDuration : getTrialDurationSeconds();
            $trialDuration = max(60, min(86400, $trialDuration));
            if ($trialDevice === '') {
                $response = ['code' => 401, 'message' => '设备ID不能为空'];
                break;
            }
            $trials = readTrialSessions();
            $existingTrial = $trials[$trialDevice] ?? null;
            $now = time();
            if ($existingTrial) {
                if (($existingTrial['expires_at'] ?? 0) > $now) {
                    $response = [
                        'code' => 200,
                        'message' => '试用进行中',
                        'data' => [
                            'device_id' => $trialDevice,
                            'expires_at' => $existingTrial['expires_at'],
                            'seconds_left' => max(0, $existingTrial['expires_at'] - $now)
                        ]
                    ];
                } else {
                    $response = [
                        'code' => 409,
                        'message' => '试用已结束，无法再次使用'
                    ];
                }
                break;
            }
            $trials[$trialDevice] = [
                'device_id' => $trialDevice,
                'started_at' => date('Y-m-d H:i:s', $now),
                'expires_at' => $now + $trialDuration,
                'duration' => $trialDuration,
                'app_id' => $requestedApp
            ];
            writeTrialSessions($trials);
            addLog('trial_start', $_SESSION['user_id'] ?? 'anonymous', ['device_id' => $trialDevice, 'duration' => $trialDuration]);
            $response = [
                'code' => 200,
                'message' => '试用启动成功',
                'data' => [
                    'device_id' => $trialDevice,
                    'expires_at' => $trials[$trialDevice]['expires_at'],
                    'seconds_left' => $trialDuration,
                    'app_id' => $requestedApp,
                    'app_name' => $applicationsById[$requestedApp]['name'] ?? $requestedApp
                ]
            ];
            break;
        case 'card_app':
            $lookupKey = trim($payload['card_key'] ?? ($_GET['card_key'] ?? ''));
            if ($lookupKey === '') {
                $response = ['code' => 400, 'message' => 'card_key不能为空'];
                break;
            }
            if (!isset($cardByKey[$lookupKey])) {
                $response = ['code' => 404, 'message' => '卡密不存在'];
                break;
            }
            $card = $cardByKey[$lookupKey];
            $appId = $card['app_id'] ?? 'app_general';
            $response = [
                'code' => 200,
                'message' => '查询成功',
                'data' => [
                    'card_key' => $card['card_key'],
                    'type' => $card['type'],
                    'status' => $card['status'],
                    'app_id' => $appId,
                    'app_name' => $applicationsById[$appId]['name'] ?? $appId,
                    'max_devices' => $card['max_devices'] ?? 1,
                    'expire_time' => $card['expire_time'] ?? null,
                    'agent_id' => $card['agent_id'] ?? null
                ]
            ];
            break;
        case 'notifications':
            $userId = $_SESSION['user_id'] ?? '';
            $notifications = readNotifications();
            $response = ['code' => 200, 'data' => array_values(array_filter($notifications, fn($n) => $n['user_id'] === $userId))];
            break;
        case 'mark_notification_read':
            $notifications = readNotifications();
            foreach ($notifications as &$notification) {
                if ($notification['id'] === ($payload['notification_id'] ?? '')) {
                    $notification['read'] = true;
                    break;
                }
            }
            writeNotifications($notifications);
            $response = ['code' => 200, 'message' => '已标记'];
            break;
    }

    addLog('api_' . $action, $_SESSION['user_id'] ?? 'anonymous', [
        'ip' => $clientIP,
        'status_code' => $response['code'] ?? 0,
        'payload_hash' => substr(sha1($rawInput), 0, 16)
    ]);
    echo json_encode($response, JSON_UNESCAPED_UNICODE);
    exit;
}

if (isset($_GET['health'])) {
    header('Content-Type: application/json');
    echo json_encode([
        'status' => 'ok',
        'timestamp' => date('Y-m-d H:i:s'),
        'system' => getSystemStatus()
    ], JSON_UNESCAPED_UNICODE);
    exit;
}

if (isset($_GET['export']) && $_GET['export'] === 'cards') {
    if (!isLoggedIn()) {
        http_response_code(401);
        exit;
    }
    $data = readData();
    $accounts = readAccounts();
    $userLookup = ['admin' => '管理员'];
    foreach ($accounts as $acc) {
        if (isset($acc['id'], $acc['username'])) {
            $userLookup[$acc['id']] = $acc['username'];
        }
    }
    $visibleCards = isAdmin() ? $data : filterCardsForAgent($data, $_SESSION['username'], $_SESSION['user_id'], $_SESSION['agent_app_id'] ?? 'all');
    $idsParam = trim($_GET['ids'] ?? '');
    if ($idsParam !== '') {
        $idsFilter = array_flip(array_filter(array_map('trim', explode(',', $idsParam))));
        $visibleCards = array_values(array_filter($visibleCards, function ($card) use ($idsFilter) {
            return isset($idsFilter[$card['id']]);
        }));
    }
    $format = $_GET['format'] ?? 'csv';
    if ($format === 'json') {
        header('Content-Type: application/json');
        header('Content-Disposition: attachment; filename="cards_' . date('Y-m-d_H-i-s') . '.json"');
        echo json_encode($visibleCards, JSON_UNESCAPED_UNICODE | JSON_PRETTY_PRINT);
        exit;
    }
    header('Content-Type: text/csv; charset=utf-8');
    header('Content-Disposition: attachment; filename="cards_' . date('Y-m-d_H-i-s') . '.csv"');
    $output = fopen('php://output', 'w');
    fwrite($output, "\xEF\xBB\xBF");
    fputcsv($output, ['卡密', '类型', '状态', '设备数', '到期时间', '应用', '生成者', '备注']);
    foreach ($visibleCards as $card) {
        $owner = getCardOwnerLabel($card, $userLookup);
        $appName = $applicationsById[$card['app_id'] ?? 'app_general']['name'] ?? '通用';
        fputcsv($output, [
            $card['card_key'],
            $cardTypes[$card['type']]['name'] ?? $card['type'],
            ($card['disabled'] ?? false) ? '已禁用' : ($card['status'] === 'unused' ? '未使用' : '已激活'),
            $card['max_devices'] ?? 1,
            $card['expire_time'] ?? '-',
            $appName,
            $owner,
            $card['notes'] ?? '-'
        ]);
    }
    fclose($output);
    exit;
}

if ($_SERVER['REQUEST_METHOD'] === 'POST' && ($_POST['action'] ?? '') === 'login') {
    $username = trim($_POST['username'] ?? '');
    $password = trim($_POST['password'] ?? '');
    $userType = $_POST['user_type'] ?? 'admin';

    if ($userType === 'admin') {
        if ($username === 'admin' && $password === 'liwei520') {
            $_SESSION['user_type'] = 'admin';
            $_SESSION['username'] = 'admin';
            $_SESSION['user_id'] = 'admin';
            $_SESSION['agent_app_id'] = 'all';
            addLog('admin_login', 'admin');
            header('Location: ' . $_SERVER['PHP_SELF']);
            exit;
        }
        $_SESSION['error'] = '管理员用户名或密码错误';
    } else {
        $accounts = readAccounts();
        foreach ($accounts as $account) {
            if ($account['username'] === $username && $account['password'] === $password && $account['type'] === 'agent') {
                $_SESSION['user_type'] = 'agent';
                $_SESSION['username'] = $username;
                $_SESSION['user_id'] = $account['id'];
                $_SESSION['agent_app_id'] = $account['app_id'] ?? 'all';
                addLog('agent_login', $account['id']);
                header('Location: ' . $_SERVER['PHP_SELF']);
                exit;
            }
        }
        $_SESSION['error'] = '代理用户名或密码错误';
    }
    header('Location: ' . $_SERVER['PHP_SELF']);
    exit;
}

if (isset($_GET['action']) && $_GET['action'] === 'logout') {
    addLog('logout', $_SESSION['user_id'] ?? 'system');
    session_destroy();
    header('Location: ' . $_SERVER['PHP_SELF']);
    exit;
}

if (!isLoggedIn()) {
    include __DIR__ . '/login_view.php';
    exit;
}

if (isAgent()) {
    $accounts = readAccounts();
    foreach ($accounts as $account) {
        if (($account['id'] ?? '') === ($_SESSION['user_id'] ?? '')) {
            $scope = $account['app_id'] ?? 'all';
            if (!isset($_SESSION['agent_app_id']) || $_SESSION['agent_app_id'] !== $scope) {
                $_SESSION['agent_app_id'] = $scope;
            }
            break;
        }
    }
}
$agentAppScope = $_SESSION['agent_app_id'] ?? 'all';

if (($config['backup']['auto_backup'] ?? false)) {
    if (!is_dir($backupsDir)) {
        mkdir($backupsDir, 0755, true);
    }
    $marker = $backupsDir . '.last';
    $last = file_exists($marker) ? (int) file_get_contents($marker) : 0;
    if (time() - $last >= ($config['backup']['backup_interval'] ?? 86400)) {
        autoBackup();
        file_put_contents($marker, (string) time());
    }
}

if ($_SERVER['REQUEST_METHOD'] === 'POST' && ($_POST['action'] ?? '') !== 'login') {
    $action = $_POST['action'] ?? '';

if (in_array($action, ['add_agent', 'edit_agent', 'delete_agent', 'update_points_config', 'add_app', 'delete_app'], true)) {
        if (!isAdmin()) {
            $_SESSION['error'] = '权限不足';
            header('Location: ' . $_SERVER['PHP_SELF'] . '?tab=agents');
            exit;
        }
        $accounts = readAccounts();
        $redirectTab = 'agents';
        switch ($action) {
            case 'add_agent':
                $username = trim($_POST['username'] ?? '');
                $password = trim($_POST['password'] ?? '');
                $points = max(0, (int) ($_POST['points'] ?? 0));
                $agentApp = $_POST['app_id'] ?? 'all';
                if ($username === '' || $password === '') {
                    $_SESSION['error'] = '用户名和密码不能为空';
                    break;
                }
                foreach ($accounts as $account) {
                    if ($account['username'] === $username) {
                        $_SESSION['error'] = '该用户名已存在';
                        $username = '';
                        break 2;
                    }
                }
                $accounts[] = [
                    'id' => uniqid('agent_', true),
                    'username' => $username,
                    'password' => $password,
                    'type' => 'agent',
                    'points' => $points,
                    'app_id' => $agentApp,
                    'created_at' => date('Y-m-d H:i:s')
                ];
                writeAccounts($accounts);
                $_SESSION['message'] = '代理添加成功';
                break;
            case 'edit_agent':
                $agentId = $_POST['agent_id'] ?? '';
                $newPoints = isset($_POST['points']) ? max(0, (int) $_POST['points']) : null;
                $newPassword = trim($_POST['password'] ?? '');
                $newAppId = $_POST['app_id'] ?? null;
                $updated = false;
                foreach ($accounts as &$account) {
                    if ($account['id'] === $agentId && $account['type'] === 'agent') {
                        if ($newPoints !== null) {
                            $account['points'] = $newPoints;
                            $updated = true;
                        }
                        if ($newPassword !== '') {
                            $account['password'] = $newPassword;
                            $updated = true;
                        }
                        if ($newAppId !== null && $newAppId !== '') {
                            $account['app_id'] = $newAppId;
                            $updated = true;
                        }
                        break;
                    }
                }
                if ($updated) {
                    writeAccounts($accounts);
                    $_SESSION['message'] = '代理信息已更新';
                } else {
                    $_SESSION['error'] = '未找到该代理或没有可更新的数据';
                }
                break;
            case 'delete_agent':
                $agentId = $_POST['agent_id'] ?? '';
                $before = count($accounts);
                $accounts = array_values(array_filter($accounts, function ($account) use ($agentId) {
                    return !($account['id'] === $agentId && $account['type'] === 'agent');
                }));
                if (count($accounts) < $before) {
                    writeAccounts($accounts);
                    $_SESSION['message'] = '代理已删除';
                } else {
                    $_SESSION['error'] = '未找到该代理';
                }
                break;
            case 'update_points_config':
                $incoming = $_POST['points'] ?? [];
                $newConfig = [];
                foreach ($cardTypes as $type => $info) {
                    $value = $incoming[$type] ?? ($info['points'] ?? 0);
                    $newConfig[$type] = max(0, (int) $value);
                }
                writeJsonFile($cardPointsFile, $newConfig);
                $_SESSION['message'] = '积分配置已更新';
                break;
            case 'add_app':
                $redirectTab = 'apps';
                $apps = readApplications();
                $name = trim($_POST['app_name'] ?? '');
                $description = trim($_POST['app_description'] ?? '');
                $appId = trim($_POST['app_id'] ?? '');
                if ($name === '') {
                    $_SESSION['error'] = '应用名称不能为空';
                    break;
                }
                if ($appId === '') {
                    $appId = 'app_' . substr(bin2hex(random_bytes(6)), 0, 6);
                }
                foreach ($apps as $app) {
                    if (($app['id'] ?? '') === $appId) {
                        $_SESSION['error'] = '应用ID已存在';
                        $appId = '';
                        break 2;
                    }
                }
                $apps[] = [
                    'id' => $appId,
                    'name' => $name,
                    'description' => $description
                ];
                writeApplications($apps);
                $_SESSION['message'] = '应用已创建';
                break;
            case 'delete_app':
                $redirectTab = 'apps';
                $appId = $_POST['app_id'] ?? '';
                if ($appId === '' || $appId === 'app_general') {
                    $_SESSION['error'] = '无法删除该应用';
                    break;
                }
                $apps = readApplications();
                $remaining = array_values(array_filter($apps, fn($app) => ($app['id'] ?? '') !== $appId));
                if (count($remaining) === count($apps)) {
                    $_SESSION['error'] = '应用不存在';
                    break;
                }
                $data = readData();
                foreach ($data as $card) {
                    if (($card['app_id'] ?? 'app_general') === $appId) {
                        $_SESSION['error'] = '应用仍有关联卡密，无法删除';
                        $appId = '';
                        break 2;
                    }
                }
                writeApplications($remaining);
                foreach ($accounts as &$account) {
                    if (($account['app_id'] ?? '') === $appId) {
                        $account['app_id'] = 'all';
                    }
                }
                writeAccounts($accounts);
                $_SESSION['message'] = '应用已删除';
                break;
        }
        header('Location: ' . $_SERVER['PHP_SELF'] . '?tab=' . $redirectTab);
        exit;
    }

    $cards = readData();
    $devices = readDevices();
    $needsSave = false;

    $cardId = $_POST['card_id'] ?? '';
    $extra = $_POST['extra'] ?? '';

    $findCard = function () use (&$cards, $cardId) {
        foreach ($cards as $index => $card) {
            if ($card['id'] === $cardId) {
                return $index;
            }
        }
        return null;
    };

    switch ($action) {
        case 'generate_cards':
            $count = max(1, min(200, (int) ($_POST['count'] ?? 1)));
            $length = max(6, min(32, (int) ($_POST['length'] ?? 16)));
            $type = $_POST['type'] ?? 'month';
            $maxDevices = max(1, min(999, (int) ($_POST['max_devices'] ?? 1)));
            $group = $_POST['group'] ?? 'normal';
            $notes = trim($_POST['notes'] ?? '');
            $isAgentUser = isAgent();
            if ($notes === '') {
                $notes = $isAgentUser ? '代理生成: ' . ($_SESSION['username'] ?? '代理') : '管理员生成';
            }
            $selectedApp = $_POST['app_id'] ?? 'app_general';
            if (!isset($applicationsById[$selectedApp])) {
                $selectedApp = 'app_general';
            }
            if ($isAgentUser && $agentAppScope !== 'all') {
                $selectedApp = $agentAppScope;
            }
            $typeCatalog = getCardTypesWithDynamicPoints();
            $typeInfo = $typeCatalog[$type] ?? ['name' => $type, 'points' => 0];
            $costPerCard = (int) ($typeInfo['points'] ?? 0);

            $agentAccounts = null;
            $agentIndex = null;
            if ($isAgentUser) {
                $agentAccounts = readAccounts();
                foreach ($agentAccounts as $idx => $account) {
                    if (($account['id'] ?? '') === ($_SESSION['user_id'] ?? '') && ($account['type'] ?? '') === 'agent') {
                        $agentIndex = $idx;
                        break;
                    }
                }
                if ($agentIndex === null) {
                    $_SESSION['error'] = '代理账户不存在';
                    header('Location: ' . $_SERVER['PHP_SELF']);
                    exit;
                }
                $requiredPoints = $costPerCard * $count;
                if (($agentAccounts[$agentIndex]['points'] ?? 0) < $requiredPoints) {
                    $_SESSION['error'] = '积分不足，需要 ' . $requiredPoints . ' 积分，当前 ' . ($agentAccounts[$agentIndex]['points'] ?? 0);
                    header('Location: ' . $_SERVER['PHP_SELF']);
                    exit;
                }
            }

            $created = 0;
            for ($i = 0; $i < $count; $i++) {
                $key = generateCardKey($length);
                if (array_filter($cards, fn($c) => $c['card_key'] === $key)) {
                    continue;
                }
                $cards[] = [
                    'id' => uniqid('card_', true),
                    'card_key' => $key,
                    'type' => $type,
                    'max_devices' => $maxDevices,
                    'status' => 'unused',
                    'disabled' => false,
                    'created_at' => date('Y-m-d H:i:s'),
                    'used_at' => null,
                    'expire_time' => null,
                    'used_by' => null,
                    'notes' => $notes,
                    'group' => $group,
                    'created_by' => $_SESSION['user_id'],
                    'agent_id' => $isAgentUser ? $_SESSION['user_id'] : null,
                    'app_id' => $selectedApp,
                    'points_spent' => $isAgentUser ? $costPerCard : 0
                ];
                $created++;
            }
            $needsSave = $created > 0;
            $failed = max(0, $count - $created);
            $logDetails = [
                'type' => $type,
                'requested' => $count,
                'success' => $created,
                'failed' => $failed
            ];

            if ($needsSave) {
                if ($isAgentUser) {
                    $actualCost = $costPerCard * $created;
                    if ($actualCost > 0 && $agentIndex !== null) {
                        $agentAccounts[$agentIndex]['points'] -= $actualCost;
                        writeAccounts($agentAccounts);
                        $_SESSION['message'] = "成功生成 {$created} 个{$typeInfo['name']}，消耗 {$actualCost} 积分";
                        $logDetails['points_used'] = $actualCost;
                    } else {
                        $_SESSION['message'] = "成功生成 {$created} 个{$typeInfo['name']}。";
                    }
                } else {
                    $_SESSION['message'] = "成功生成 {$created} 个{$typeInfo['name']}，失败 {$failed} 个";
                }
            } else {
                $_SESSION['error'] = '未生成新卡密';
            }

            addLog('generate_cards', $_SESSION['user_id'], $logDetails);
            break;
        case 'delete_card':
            $index = $findCard();
            if ($index !== null && cardVisibleToCurrentUser($cards[$index])) {
                $cardKey = $cards[$index]['card_key'];
                array_splice($cards, $index, 1);
                unset($devices[$cardKey]);
                $needsSave = true;
                writeDevices($devices);
                $_SESSION['message'] = '卡密已删除';
                addLog('delete_card', $_SESSION['user_id'], ['card' => $cardKey]);
            }
            break;
        case 'toggle_disable':
            $index = $findCard();
            if ($index !== null && cardVisibleToCurrentUser($cards[$index])) {
                $cards[$index]['disabled'] = !($cards[$index]['disabled'] ?? false);
                $needsSave = true;
                $_SESSION['message'] = $cards[$index]['disabled'] ? '卡密已禁用' : '卡密已启用';
            }
            break;
        case 'update_max_devices':
            $index = $findCard();
            if ($index !== null && cardVisibleToCurrentUser($cards[$index])) {
                $value = max(1, min(999, (int) $extra));
                $cards[$index]['max_devices'] = $value;
                $needsSave = true;
                $_SESSION['message'] = '多开数量已更新';
            }
            break;
        case 'add_notes':
            $index = $findCard();
            if ($index !== null && cardVisibleToCurrentUser($cards[$index])) {
                $cards[$index]['notes'] = $extra;
                $needsSave = true;
                $_SESSION['message'] = '备注已更新';
            }
            break;
        case 'adjust_days':
            $index = $findCard();
            if ($index !== null && cardVisibleToCurrentUser($cards[$index])) {
                $days = (int) $extra;
                $deltaPoints = calculatePointsDeltaForDays($cards[$index], $days);
                if ($deltaPoints !== 0) {
                    $creatorId = $cards[$index]['created_by'] ?? '';
                    $pointError = null;
                    if ($deltaPoints > 0) {
                        if (!changeAgentPoints($creatorId, -$deltaPoints, $pointError)) {
                            $_SESSION['error'] = $pointError ?? '积分不足，无法增加天数';
                            break;
                        }
                    } else {
                        changeAgentPoints($creatorId, abs($deltaPoints));
                    }
                    $cards[$index]['points_spent'] = max(0, ($cards[$index]['points_spent'] ?? 0) + $deltaPoints);
                }
                $cards[$index] = adjustCardExpireDays($cards[$index], $days, getCardTypesWithDynamicPoints());
                $needsSave = true;
                $_SESSION['message'] = "已调整 {$days} 天" . ($deltaPoints !== 0 ? "，积分变动 {$deltaPoints}" : '');
            }
            break;
        case 'batch_delete':
            $ids = array_filter(array_map('trim', explode(',', $extra)));
            if (empty($ids)) {
                $_SESSION['error'] = '请选择要删除的卡密';
                break;
            }
            $idsLookup = array_flip($ids);
            $newCards = [];
            $removed = 0;
            foreach ($cards as $card) {
                if (isset($idsLookup[$card['id']]) && cardVisibleToCurrentUser($card)) {
                    $removed++;
                    $cardKey = $card['card_key'];
                    unset($devices[$cardKey]);
                } else {
                    $newCards[] = $card;
                }
            }
            if ($removed > 0) {
                $cards = array_values($newCards);
                writeDevices($devices);
                $needsSave = true;
                $_SESSION['message'] = "已删除 {$removed} 个卡密";
                addLog('batch_delete', $_SESSION['user_id'], ['count' => $removed]);
            } else {
                $_SESSION['error'] = '没有可删除的卡密或权限不足';
            }
            break;
    }

    if ($needsSave) {
        writeData($cards);
    }

    header('Location: ' . $_SERVER['PHP_SELF']);
    exit;
}

$allCards = readData();
$devices = readDevices();
$accounts = readAccounts();
$userLookup = ['admin' => '管理员'];
$currentAgentPoints = null;
foreach ($accounts as $account) {
    if (isset($account['id'], $account['username'])) {
        $userLookup[$account['id']] = $account['username'];
    }
    if (isAgent() && ($account['id'] ?? '') === ($_SESSION['user_id'] ?? '')) {
        $currentAgentPoints = $account['points'] ?? 0;
    }
}
$agentAccounts = array_values(array_filter($accounts, fn($acc) => ($acc['type'] ?? '') === 'agent'));
if (isAgent()) {
    $allCards = filterCardsForAgent($allCards, $_SESSION['username'], $_SESSION['user_id'], $agentAppScope);
}

$cardGroups = $config['card_groups'] ?? ['normal' => ['name' => '默认分组', 'color' => '#4CAF50']];

$search = trim($_GET['search'] ?? '');
$statusFilter = $_GET['status'] ?? 'all';
$typeFilter = $_GET['type'] ?? 'all';
$groupFilter = $_GET['group'] ?? 'all';

$filteredCards = array_values(array_filter($allCards, function ($card) use ($search, $statusFilter, $typeFilter, $groupFilter) {
    $matchSearch = $search === '' || stripos($card['card_key'], $search) !== false || stripos($card['notes'] ?? '', $search) !== false || stripos($card['used_by'] ?? '', $search) !== false;
    $matchStatus = $statusFilter === 'all' || ($card['disabled'] ?? false && $statusFilter === 'disabled') || ($card['status'] === $statusFilter);
    $matchType = $typeFilter === 'all' || $card['type'] === $typeFilter;
    $matchGroup = $groupFilter === 'all' || (($card['group'] ?? 'normal') === $groupFilter);
    return $matchSearch && $matchStatus && $matchType && $matchGroup;
}));

$totalCards = count($filteredCards);
$unusedCount = count(array_filter($filteredCards, fn($c) => $c['status'] === 'unused'));
$usedCount = count(array_filter($filteredCards, fn($c) => $c['status'] === 'used'));
$disabledCount = count(array_filter($filteredCards, fn($c) => $c['disabled'] ?? false));

$perPage = 50;
$page = max(1, (int) ($_GET['page'] ?? 1));
$totalPages = max(1, (int) ceil($totalCards / $perPage));
$page = min($page, $totalPages);
$offset = ($page - 1) * $perPage;
$visibleCards = array_slice($filteredCards, $offset, $perPage);

$systemStatus = getSystemStatus();
$dynamicCardTypes = getCardTypesWithDynamicPoints();

$appStats = [];
foreach ($applicationsById as $appId => $app) {
    $appStats[$appId] = [
        'id' => $appId,
        'name' => $app['name'] ?? $appId,
        'cards' => 0,
        'online' => 0
    ];
}
$now = time();
foreach ($allCards as $card) {
    $appId = $card['app_id'] ?? 'app_general';
    if (!isset($appStats[$appId])) {
        $appStats[$appId] = [
            'id' => $appId,
            'name' => $appId,
            'cards' => 0,
            'online' => 0
        ];
    }
    $appStats[$appId]['cards']++;
    $cardDevices = $devices[$card['card_key']] ?? [];
    foreach ($cardDevices as $device) {
        $status = $device['status'] ?? 'online';
        if ($status === 'kicked') {
            continue;
        }
        $lastHeartbeat = $device['last_heartbeat'] ?? $device['login_time'] ?? null;
        $lastTs = $lastHeartbeat ? strtotime($lastHeartbeat) : 0;
        if ($lastTs && ($now - $lastTs) <= 300) {
            $appStats[$appId]['online']++;
        }
    }
}
$appStatsDisplay = $appStats;
if (isAgent() && $agentAppScope !== 'all') {
    $appStatsDisplay = array_filter($appStats, fn($stat) => $stat['id'] === $agentAppScope);
}

$availableApps = $applications;
if (isAgent() && $agentAppScope !== 'all') {
    $availableApps = array_values(array_filter($applications, fn($app) => ($app['id'] ?? '') === $agentAppScope));
    if (empty($availableApps)) {
        $placeholder = [
            'id' => $agentAppScope,
            'name' => $applicationsById[$agentAppScope]['name'] ?? $agentAppScope,
            'description' => '代理专用应用'
        ];
        $availableApps = [$placeholder];
        $applicationsById[$agentAppScope] = $placeholder;
    }
} elseif (empty($availableApps)) {
    $availableApps = [ $applicationsById['app_general'] ];
}

$trialSessions = readTrialSessions();
$activeTrials = [];
$now = time();
foreach ($trialSessions as $trial) {
    $expires = (int) ($trial['expires_at'] ?? 0);
    if ($expires > $now) {
        $trial['expires_at'] = $expires;
        $trial['seconds_left'] = $expires - $now;
        $activeTrials[] = $trial;
    }
}
$activeTrialsDisplay = $activeTrials;

include __DIR__ . '/main_view.php';
