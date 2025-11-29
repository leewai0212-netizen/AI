<?php
session_start();

$dataFile = __DIR__ . '/card_keys.json';
$devicesFile = __DIR__ . '/devices.json';
$accountsFile = __DIR__ . '/accounts.json';
$logsFile = __DIR__ . '/system_logs.json';
$notificationsFile = __DIR__ . '/notifications.json';
$configFile = __DIR__ . '/system_config.json';
$backupsDir = __DIR__ . '/backups/';
$cardPointsFile = __DIR__ . '/card_points_config.json';

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
    $cpu = isset($load[0]) ? round($load[0] * 100, 1) : 0;
    $memoryUsage = round(memory_get_usage(true) / 1048576, 2);
    $memoryPeak = round(memory_get_peak_usage(true) / 1048576, 2);
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
        'memory_peak' => $memoryPeak,
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
    $path = '/proc/uptime';
    if (file_exists($path)) {
        $parts = explode(' ', trim((string) file_get_contents($path)));
        $seconds = (float) ($parts[0] ?? 0);
        $days = floor($seconds / 86400);
        $hours = floor(($seconds % 86400) / 3600);
        $minutes = floor(($seconds % 3600) / 60);
        return sprintf('%d天 %d小时 %d分钟', $days, $hours, $minutes);
    }
    return '未知';
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

function readDevices(): array {
    global $devicesFile;
    return readJsonFile($devicesFile, []);
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

function generateCardKey(int $length = 16): string {
    $pool = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789';
    $max = strlen($pool) - 1;
    $key = '';
    for ($i = 0; $i < $length; $i++) {
        $key .= $pool[random_int(0, $max)];
    }
    return $key;
}

function filterCardsForAgent(array $cards, string $agentName, string $agentId): array {
    return array_values(array_filter($cards, function ($card) use ($agentName, $agentId) {
        if (($card['created_by'] ?? '') === $agentId) {
            return true;
        }
        $notes = $card['notes'] ?? '';
        return strpos($notes, '代理生成: ' . $agentName) !== false ||
            strpos($notes, '代理提卡: ' . $agentName) !== false;
    }));
}

function cardVisibleToCurrentUser(array $card): bool {
    if (isAdmin()) {
        return true;
    }
    if (isAgent()) {
        $agentId = $_SESSION['user_id'] ?? '';
        $agentName = $_SESSION['username'] ?? '';
        return filterCardsForAgent([$card], $agentName, $agentId) !== [];
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

initSystemConfig();
initDatabase();

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

    $action = $_GET['api'];
    $payload = json_decode(file_get_contents('php://input'), true);
    if (!$payload) {
        $payload = $_POST;
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
                    'expire_time' => $card['expire_time'],
                    'max_devices' => $maxDevices,
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
            if ($card['status'] === 'unused' || ($card['disabled'] ?? false)) {
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
                    'expire_time' => $card['expire_time'],
                    'online_count' => $result['online_count'],
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

    addLog('api_' . $action, $_SESSION['user_id'] ?? 'anonymous', ['ip' => $clientIP]);
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

if (isset($_GET['export']) && isLoggedIn()) {
    $data = readData();
    $visibleCards = isAdmin() ? $data : filterCardsForAgent($data, $_SESSION['username'], $_SESSION['user_id']);
    header('Content-Type: text/csv; charset=utf-8');
    header('Content-Disposition: attachment; filename="cards_' . date('Ymd_His') . '.csv"');
    $output = fopen('php://output', 'w');
    fwrite($output, "\xEF\xBB\xBF");
    fputcsv($output, ['卡密', '类型', '状态', '到期时间', '设备数', '备注']);
    foreach ($visibleCards as $card) {
        fputcsv($output, [
            $card['card_key'],
            $cardTypes[$card['type']]['name'] ?? $card['type'],
            $card['disabled'] ?? false ? '已禁用' : ($card['status'] === 'unused' ? '未使用' : '已激活'),
            $card['expire_time'] ?? '-',
            $card['max_devices'] ?? 1,
            $card['notes'] ?? ''
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

    if (in_array($action, ['add_agent', 'edit_agent', 'delete_agent'], true)) {
        if (!isAdmin()) {
            $_SESSION['error'] = '权限不足';
            header('Location: ' . $_SERVER['PHP_SELF'] . '?tab=agents');
            exit;
        }
        $accounts = readAccounts();
        switch ($action) {
            case 'add_agent':
                $username = trim($_POST['username'] ?? '');
                $password = trim($_POST['password'] ?? '');
                $points = max(0, (int) ($_POST['points'] ?? 0));
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
                    'created_at' => date('Y-m-d H:i:s')
                ];
                writeAccounts($accounts);
                $_SESSION['message'] = '代理添加成功';
                break;
            case 'edit_agent':
                $agentId = $_POST['agent_id'] ?? '';
                $newPoints = isset($_POST['points']) ? max(0, (int) $_POST['points']) : null;
                $newPassword = trim($_POST['password'] ?? '');
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
        }
        header('Location: ' . $_SERVER['PHP_SELF'] . '?tab=agents');
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
            $maxDevices = max(1, min(10, (int) ($_POST['max_devices'] ?? 1)));
            $group = $_POST['group'] ?? 'normal';
            $notes = trim($_POST['notes'] ?? '');
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
                    'created_by' => $_SESSION['user_id']
                ];
                $created++;
            }
            $needsSave = $created > 0;
            $_SESSION['message'] = $created ? "成功生成 {$created} 个卡密" : '未生成新卡密';
            addLog('generate_cards', $_SESSION['user_id'], ['count' => $created]);
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
        case 'reset_card':
            $index = $findCard();
            if ($index !== null && cardVisibleToCurrentUser($cards[$index])) {
                $cards[$index]['status'] = 'unused';
                $cards[$index]['disabled'] = false;
                $cards[$index]['used_at'] = null;
                $cards[$index]['expire_time'] = null;
                $cards[$index]['used_by'] = null;
                $cardKey = $cards[$index]['card_key'];
                unset($devices[$cardKey]);
                writeDevices($devices);
                $needsSave = true;
                $_SESSION['message'] = '卡密已重置';
            }
            break;
        case 'update_max_devices':
            $index = $findCard();
            if ($index !== null && cardVisibleToCurrentUser($cards[$index])) {
                $value = max(1, min(10, (int) $extra));
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
                $cards[$index] = adjustCardExpireDays($cards[$index], $days, getCardTypesWithDynamicPoints());
                $needsSave = true;
                $_SESSION['message'] = "已调整 {$days} 天";
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
$agentAccounts = array_values(array_filter($accounts, fn($acc) => ($acc['type'] ?? '') === 'agent'));

if (isAgent()) {
    $allCards = filterCardsForAgent($allCards, $_SESSION['username'], $_SESSION['user_id']);
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

include __DIR__ . '/main_view.php';
