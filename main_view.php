<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>卡密管理系统</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * { box-sizing: border-box; }
        body {
            margin: 0;
            font-family: 'Segoe UI', 'PingFang SC', sans-serif;
            background: #f5f6fb;
            color: #333;
        }
        header {
            background: linear-gradient(135deg, #667eea, #764ba2);
            color: #fff;
            padding: 24px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        header h1 { margin: 0; font-size: 24px; }
        header .user-info { display: flex; gap: 12px; align-items: center; }
        header a {
            color: #fff;
            text-decoration: none;
            border: 1px solid rgba(255,255,255,0.6);
            padding: 6px 16px;
            border-radius: 999px;
        }
        .container { max-width: 1280px; margin: 0 auto; padding: 24px; }
        .tabs { display: flex; gap: 12px; border-bottom: 1px solid #e0e0e0; margin-bottom: 24px; }
        .tab {
            padding: 10px 18px;
            cursor: pointer;
            border-bottom: 3px solid transparent;
            font-weight: 600;
            color: #888;
        }
        .tab.active { border-color: #667eea; color: #333; }
        .tab-content { display: none; }
        .tab-content.active { display: block; }
        .stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 16px; margin-bottom: 24px; }
        .stat-card {
            background: #fff;
            border-radius: 12px;
            padding: 16px;
            box-shadow: 0 8px 20px rgba(0,0,0,0.05);
        }
        .stat-card h3 { margin: 0 0 8px; font-size: 14px; color: #888; }
        .stat-card p { margin: 0; font-size: 26px; font-weight: 600; }
        form.inline-form { display: flex; flex-wrap: wrap; gap: 12px; margin-bottom: 16px; }
        form.inline-form input,
        form.inline-form select,
        form.inline-form button {
            padding: 10px 14px;
            border-radius: 8px;
            border: 1px solid #dcdcdc;
            font-size: 14px;
        }
        form.inline-form button {
            background: #667eea;
            border: none;
            color: #fff;
            cursor: pointer;
        }
        table { width: 100%; border-collapse: collapse; background: #fff; border-radius: 12px; overflow: hidden; }
        th, td { padding: 12px 14px; border-bottom: 1px solid #f0f0f0; text-align: left; font-size: 13px; }
        th { background: #fafbff; font-size: 12px; color: #666; }
        tr:hover td { background: #fafafa; }
        .bulk-actions {
            display: none;
            align-items: center;
            justify-content: space-between;
            background: #fff4e5;
            border: 1px solid #ffd7a3;
            border-radius: 10px;
            padding: 10px 16px;
            margin-bottom: 12px;
            font-size: 14px;
            color: #a86a00;
        }
        .bulk-actions.active { display: flex; }
        .bulk-actions button {
            background: linear-gradient(135deg, #ff8a65, #ff7043);
            color: #fff;
        }
        .points-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
            gap: 12px;
            width: 100%;
        }
        .points-grid label {
            display: flex;
            flex-direction: column;
            font-size: 12px;
            color: #555;
        }
        .points-grid input {
            margin-top: 6px;
        }
        .tag {
            display: inline-block;
            padding: 4px 10px;
            border-radius: 999px;
            font-size: 12px;
            font-weight: 600;
        }
        .status-unused { background: #e8f7ee; color: #2e7d32; }
        .status-used { background: #e3f2fd; color: #1976d2; }
        .status-disabled { background: #fdecea; color: #c62828; }
        .actions button {
            border: none;
            background: #f0f1fa;
            color: #4a4a4a;
            border-radius: 6px;
            padding: 4px 10px;
            margin: 2px;
            font-size: 12px;
            cursor: pointer;
        }
        .actions button.danger { background: #fdecea; color: #c62828; }
        .message {
            background: #e8f5e9;
            color: #2e7d32;
            padding: 12px 16px;
            border-radius: 10px;
            margin-bottom: 16px;
        }
        .api-doc {
            background: #fff;
            border-radius: 12px;
            padding: 20px;
            box-shadow: 0 8px 24px rgba(0,0,0,0.05);
        }
        .api-block { margin-bottom: 18px; }
        .api-block pre {
            background: #272822;
            color: #f8f8f2;
            padding: 14px;
            border-radius: 10px;
            overflow-x: auto;
            white-space: pre-wrap;
        }
        .pagination { display: flex; gap: 12px; justify-content: center; margin-top: 16px; }
        .pagination button {
            border: none;
            padding: 8px 14px;
            border-radius: 8px;
            background: #fff;
            box-shadow: 0 4px 12px rgba(0,0,0,0.08);
            cursor: pointer;
        }
        .system-row { display: grid; grid-template-columns: repeat(auto-fit, minmax(160px,1fr)); gap: 12px; margin-bottom: 24px; }
        .system-card { background: #fff; border-radius: 12px; padding: 16px; text-align: center; }
        .system-card strong { display: block; font-size: 20px; margin-bottom: 6px; }
        .badge { padding: 2px 8px; border-radius: 6px; background: rgba(255,255,255,0.2); color: #fff; font-size: 12px; }
        @media (max-width: 768px) {
            .actions button { margin-bottom: 4px; }
        }
    </style>
</head>
<body>
<header>
    <div>
        <h1>阿伟定制自用卡密系统</h1>
        <div class="badge">版本 2.0.0</div>
    </div>
    <div class="user-info">
        <span><?php echo isAdmin() ? '管理员' : '代理: ' . htmlspecialchars($_SESSION['username']); ?></span>
        <a href="?action=logout">退出</a>
    </div>
</header>
<div class="container">
    <?php if (isset($_SESSION['message'])): ?>
        <div class="message"><?php echo htmlspecialchars($_SESSION['message']); unset($_SESSION['message']); ?></div>
    <?php endif; ?>
    <?php if (isset($_SESSION['error'])): ?>
        <div class="message" style="background:#fdecea;color:#c62828;"><?php echo htmlspecialchars($_SESSION['error']); unset($_SESSION['error']); ?></div>
    <?php endif; ?>
    <div class="tabs">
        <div class="tab active" data-tab="manage">卡密管理</div>
        <?php if (isAdmin()): ?>
            <div class="tab" data-tab="apps">应用管理</div>
            <div class="tab" data-tab="agents">代理管理</div>
            <div class="tab" data-tab="api">API 文档</div>
        <?php endif; ?>
    </div>
    <div class="tab-content active" id="manage">
        <div class="stats">
            <div class="stat-card">
                <h3>总卡密</h3>
                <p><?php echo $totalCards; ?></p>
            </div>
            <div class="stat-card">
                <h3>未使用</h3>
                <p><?php echo $unusedCount; ?></p>
            </div>
            <div class="stat-card">
                <h3>已激活</h3>
                <p><?php echo $usedCount; ?></p>
            </div>
            <div class="stat-card">
                <h3>已禁用</h3>
                <p><?php echo $disabledCount; ?></p>
            </div>
        </div>
        <?php if (isAgent()): ?>
            <div class="message" style="background:#e3f2fd;color:#0d47a1;">
                <div style="font-weight:600;">当前积分：<?php echo (int) ($currentAgentPoints ?? 0); ?></div>
                <div style="margin-top:10px;">
                    <strong>生成消耗：</strong>
                </div>
                <div class="points-grid" style="margin-top:6px;">
                    <?php foreach ($dynamicCardTypes as $info): ?>
                        <label style="font-size:13px;color:#333;">
                            <?php echo $info['name']; ?>
                            <span style="margin-top:4px;font-weight:bold;"><?php echo (int) ($info['points'] ?? 0); ?> 积分/张</span>
                        </label>
                    <?php endforeach; ?>
                </div>
            </div>
        <?php endif; ?>
        <?php if (isAdmin()): ?>
        <div class="system-row">
            <div class="system-card">
                <strong><?php echo $systemStatus['cpu_usage']; ?>%</strong>
                <span>CPU 使用率</span>
            </div>
            <div class="system-card">
                <strong><?php echo $systemStatus['memory_usage']; ?>MB</strong>
                <span>内存占用</span>
            </div>
            <div class="system-card">
                <strong><?php echo $systemStatus['active_connections']; ?></strong>
                <span>在线设备</span>
            </div>
            <div class="system-card">
                <strong><?php echo htmlspecialchars($systemStatus['uptime']); ?></strong>
                <span>运行时间</span>
            </div>
        </div>
        <?php endif; ?>
        <?php if (!empty($appStatsDisplay)): ?>
        <div class="type-stats">
            <?php foreach ($appStatsDisplay as $stat): ?>
                <div class="type-stat-card" style="background:#fff; border:1px solid #eee;">
                    <div class="type-stat-number"><?php echo $stat['online']; ?> / <?php echo $stat['cards']; ?></div>
                    <div class="type-stat-label"><?php echo htmlspecialchars($stat['name']); ?> 在线/总</div>
                </div>
            <?php endforeach; ?>
        </div>
        <?php endif; ?>
        <form class="inline-form" method="POST">
            <input type="hidden" name="action" value="generate_cards">
            <input type="number" name="count" min="1" max="200" placeholder="数量" value="1">
            <input type="number" name="length" min="6" max="32" placeholder="长度" value="8">
            <select name="type">
                <?php foreach ($dynamicCardTypes as $key => $info): ?>
                    <option value="<?php echo $key; ?>"><?php echo $info['name']; ?></option>
                <?php endforeach; ?>
            </select>
            <input type="number" name="max_devices" min="1" max="10" placeholder="多开" value="1">
            <select name="group">
                <?php foreach ($cardGroups as $groupId => $group): ?>
                    <option value="<?php echo $groupId; ?>"><?php echo $group['name']; ?></option>
                <?php endforeach; ?>
            </select>
            <?php if (isAdmin() || ($agentAppScope ?? 'all') === 'all'): ?>
                <select name="app_id">
                    <option value="app_general">通用（全部应用）</option>
                    <?php foreach ($availableApps as $app): ?>
                        <?php if (($app['id'] ?? '') === 'app_general') { continue; } ?>
                        <option value="<?php echo htmlspecialchars($app['id'], ENT_QUOTES); ?>"><?php echo htmlspecialchars($app['name']); ?></option>
                    <?php endforeach; ?>
                </select>
            <?php else: ?>
                <?php $lockedApp = $availableApps[0] ?? ['id' => 'app_general', 'name' => '通用']; ?>
                <input type="hidden" name="app_id" value="<?php echo htmlspecialchars($lockedApp['id'], ENT_QUOTES); ?>">
                <div style="font-size:13px;color:#555;">应用：<?php echo htmlspecialchars($lockedApp['name']); ?></div>
            <?php endif; ?>
            <input type="text" name="notes" placeholder="备注 (可空)">
            <button type="submit">⚡ 生成卡密</button>
            <a href="?export=cards" style="padding:10px 14px;border-radius:8px;background:#fff;border:1px solid #dcdcdc;text-decoration:none;color:#333;">📥 导出</a>
        </form>
        <form class="inline-form" method="GET">
            <input type="text" name="search" placeholder="搜索卡密/备注" value="<?php echo htmlspecialchars($search); ?>">
            <select name="status">
                <option value="all" <?php echo $statusFilter === 'all' ? 'selected' : ''; ?>>全部状态</option>
                <option value="unused" <?php echo $statusFilter === 'unused' ? 'selected' : ''; ?>>未使用</option>
                <option value="used" <?php echo $statusFilter === 'used' ? 'selected' : ''; ?>>已激活</option>
                <option value="disabled" <?php echo $statusFilter === 'disabled' ? 'selected' : ''; ?>>已禁用</option>
            </select>
            <select name="type">
                <option value="all">全部类型</option>
                <?php foreach ($cardTypes as $type => $info): ?>
                    <option value="<?php echo $type; ?>" <?php echo $typeFilter === $type ? 'selected' : ''; ?>><?php echo $info['name']; ?></option>
                <?php endforeach; ?>
            </select>
            <select name="group">
                <option value="all">全部分组</option>
                <?php foreach ($cardGroups as $groupId => $group): ?>
                    <option value="<?php echo $groupId; ?>" <?php echo $groupFilter === $groupId ? 'selected' : ''; ?>><?php echo $group['name']; ?></option>
                <?php endforeach; ?>
            </select>
            <button type="submit">🔍 筛选</button>
        </form>
        <div class="bulk-actions" id="bulkActions">
            <span>已选择 <strong id="bulkCount">0</strong> 项</span>
            <div>
                <button type="button" onclick="batchDeleteSelected()">批量删除</button>
                <button type="button" style="margin-left:8px;" onclick="batchExportSelected()">批量导出</button>
            </div>
        </div>
        <div style="overflow-x:auto;">
            <table>
                <thead>
                    <tr>
                        <th style="width:40px;">
                            <input type="checkbox" id="selectAll">
                        </th>
                        <th>卡密</th>
                        <th>类型</th>
                        <th>状态</th>
                        <th>到期时间</th>
                        <th>多开</th>
                        <th>在线/总</th>
                        <th>上次心跳</th>
                        <th>应用</th>
                        <th>生成者</th>
                        <th>分组</th>
                        <th>备注</th>
                        <th>操作</th>
                    </tr>
                </thead>
                <tbody>
                <?php if (empty($visibleCards)): ?>
                    <tr><td colspan="12" style="text-align:center;padding:40px;">暂无数据</td></tr>
                <?php else: ?>
                    <?php foreach ($visibleCards as $card):
                        $statusClass = $card['disabled'] ?? false ? 'status-disabled' : ($card['status'] === 'unused' ? 'status-unused' : 'status-used');
                        $cardKey = $card['card_key'];
                        $deviceList = $devices[$cardKey] ?? [];
                        $online = 0;
                        $lastHeartbeat = '-';
                        $lastHeartbeatTs = 0;
                        foreach ($deviceList as $device) {
                            if (($device['status'] ?? 'online') !== 'kicked') {
                                $online++;
                            }
                            if (!empty($device['last_heartbeat'])) {
                                $ts = strtotime($device['last_heartbeat']);
                                if ($ts && $ts > $lastHeartbeatTs) {
                                    $lastHeartbeatTs = $ts;
                                    $lastHeartbeat = $device['last_heartbeat'];
                                }
                            }
                        }
                        $groupId = $card['group'] ?? 'normal';
                        $groupColor = $cardGroups[$groupId]['color'] ?? '#999';
                        $typeMeta = $cardTypes[$card['type']] ?? ['name' => $card['type'], 'color' => '#999'];
                        $cardIdEsc = htmlspecialchars($card['id'], ENT_QUOTES);
                        $ownerName = htmlspecialchars(getCardOwnerLabel($card, $userLookup), ENT_QUOTES);
                        $appRecord = $applicationsById[$card['app_id'] ?? 'app_general'] ?? null;
                        $appName = htmlspecialchars($appRecord['name'] ?? ($card['app_id'] ?? '通用'));
                    ?>
                    <tr>
                        <td><input type="checkbox" class="row-check" value="<?php echo $cardIdEsc; ?>"></td>
                        <td><span style="font-family:monospace;cursor:pointer;" onclick="copyKey('<?php echo htmlspecialchars($cardKey, ENT_QUOTES); ?>')"><?php echo htmlspecialchars($cardKey); ?></span></td>
                        <td><span class="tag" style="background: <?php echo $typeMeta['color']; ?>20;color: <?php echo $typeMeta['color']; ?>;"><?php echo $typeMeta['name']; ?></span></td>
                        <td><span class="tag <?php echo $statusClass; ?>"><?php echo $card['disabled'] ?? false ? '已禁用' : ($card['status'] === 'unused' ? '未使用' : '已激活'); ?></span></td>
                        <td><?php echo $card['expire_time'] ?? '-'; ?></td>
                        <td><?php echo $card['max_devices'] ?? 1; ?></td>
                        <td><?php echo $online . '/' . count($deviceList); ?></td>
                        <td><?php echo htmlspecialchars($lastHeartbeat); ?></td>
                        <td><?php echo $appName; ?></td>
                        <td><?php echo $ownerName; ?></td>
                        <td><span class="tag" style="background: <?php echo $groupColor; ?>20;color: <?php echo $groupColor; ?>;"><?php echo $cardGroups[$groupId]['name'] ?? $groupId; ?></span></td>
                        <td><?php echo htmlspecialchars($card['notes'] ?? '-'); ?></td>
                        <td class="actions">
                            <?php if (!($card['disabled'] ?? false)): ?>
                                <button onclick="submitAction('toggle_disable','<?php echo $cardIdEsc; ?>')">禁用</button>
                            <?php else: ?>
                                <button onclick="submitAction('toggle_disable','<?php echo $cardIdEsc; ?>')">启用</button>
                            <?php endif; ?>
                            <button onclick="submitAction('reset_card','<?php echo $cardIdEsc; ?>')">重置</button>
                            <button onclick="promptMax('<?php echo $cardIdEsc; ?>','<?php echo $card['max_devices'] ?? 1; ?>')">多开</button>
                            <button onclick="promptNotes('<?php echo $cardIdEsc; ?>','<?php echo htmlspecialchars($card['notes'] ?? '', ENT_QUOTES); ?>')">备注</button>
                            <button onclick="promptDays('<?php echo $cardIdEsc; ?>')">调天数</button>
                            <?php if (isAdmin()): ?>
                                <button onclick="submitAction('recycle_card','<?php echo $cardIdEsc; ?>')">回收</button>
                            <?php endif; ?>
                            <button class="danger" onclick="confirmDelete('<?php echo $cardIdEsc; ?>')">删除</button>
                        </td>
                    </tr>
                    <?php endforeach; ?>
                <?php endif; ?>
                </tbody>
            </table>
        </div>
        <?php if ($totalPages > 1): ?>
            <div class="pagination">
                <?php if ($page > 1): ?>
                    <button onclick="goPage(<?php echo $page - 1; ?>)">上一页</button>
                <?php endif; ?>
                <span>第 <?php echo $page; ?> / <?php echo $totalPages; ?> 页</span>
                <?php if ($page < $totalPages): ?>
                    <button onclick="goPage(<?php echo $page + 1; ?>)">下一页</button>
                <?php endif; ?>
            </div>
        <?php endif; ?>
    </div>
    <?php if (isAdmin()): ?>
    <div class="tab-content" id="apps">
        <div class="api-doc">
            <h2>应用管理</h2>
            <form class="inline-form" method="POST" style="flex-direction:column; align-items:flex-start; gap:12px;">
                <input type="hidden" name="action" value="add_app">
                <div style="display:flex;flex-wrap:wrap;gap:12px;width:100%;">
                    <input type="text" name="app_name" placeholder="应用名称" required>
                    <input type="text" name="app_id" placeholder="应用ID（可留空自动生成）">
                    <input type="text" name="app_description" placeholder="备注">
                </div>
                <button type="submit">➕ 新增应用</button>
            </form>
            <div style="overflow-x:auto;margin-top:20px;">
                <table>
                    <thead>
                        <tr>
                            <th>名称</th>
                            <th>ID</th>
                            <th>备注</th>
                            <th>在线/总卡密</th>
                            <th>操作</th>
                        </tr>
                    </thead>
                    <tbody>
                        <?php foreach ($applications as $app):
                            $stat = $appStats[$app['id']] ?? ['online' => 0, 'cards' => 0];
                        ?>
                        <tr>
                            <td><?php echo htmlspecialchars($app['name']); ?></td>
                            <td><?php echo htmlspecialchars($app['id']); ?></td>
                            <td><?php echo htmlspecialchars($app['description'] ?? '-'); ?></td>
                            <td><?php echo ($stat['online'] ?? 0) . ' / ' . ($stat['cards'] ?? 0); ?></td>
                            <td class="actions">
                                <?php if (($app['id'] ?? '') !== 'app_general'): ?>
                                    <button class="danger" onclick="deleteApp('<?php echo htmlspecialchars($app['id'], ENT_QUOTES); ?>')">删除</button>
                                <?php else: ?>
                                    <span style="font-size:12px;color:#999;">默认</span>
                                <?php endif; ?>
                            </td>
                        </tr>
                        <?php endforeach; ?>
                    </tbody>
                </table>
            </div>
        </div>
    </div>
    <div class="tab-content" id="agents">
        <div class="api-doc">
            <h2>代理管理</h2>
            <p>创建、调整或删除代理账号，积分实时生效。</p>
            <h3 style="margin-top:10px;">积分配置</h3>
            <form class="inline-form" method="POST" style="flex-direction:column; align-items:flex-start; gap:12px;">
                <input type="hidden" name="action" value="update_points_config">
                <div class="points-grid">
                    <?php foreach ($dynamicCardTypes as $type => $info): ?>
                        <label>
                            <?php echo $info['name']; ?>
                            <input type="number" min="0" name="points[<?php echo $type; ?>]" value="<?php echo (int) ($info['points'] ?? 0); ?>">
                        </label>
                    <?php endforeach; ?>
                </div>
                <button type="submit">💾 保存积分配置</button>
            </form>
            <hr style="margin:24px 0;">
            <form class="inline-form" method="POST">
                <input type="hidden" name="action" value="add_agent">
                <input type="text" name="username" placeholder="用户名" required>
                <input type="password" name="password" placeholder="密码" required>
                <input type="number" name="points" min="0" placeholder="初始积分" value="0">
                <select name="app_id">
                    <option value="all">通用（可管理全部应用）</option>
                    <?php foreach ($applicationsById as $appId => $app): ?>
                        <?php if ($appId === 'app_general') continue; ?>
                        <option value="<?php echo htmlspecialchars($appId, ENT_QUOTES); ?>"><?php echo htmlspecialchars($app['name'] ?? $appId); ?></option>
                    <?php endforeach; ?>
                </select>
                <button type="submit">➕ 添加代理</button>
            </form>
            <div style="overflow-x:auto;">
                <table>
                    <thead>
                        <tr>
                            <th>用户名</th>
                            <th>积分</th>
                            <th>应用</th>
                            <th>创建时间</th>
                            <th>操作</th>
                        </tr>
                    </thead>
                    <tbody>
                        <?php if (empty($agentAccounts)): ?>
                            <tr><td colspan="5" style="text-align:center;padding:30px;">暂无代理账户</td></tr>
                        <?php else: ?>
                            <?php foreach ($agentAccounts as $agent):
                                $agentIdEsc = htmlspecialchars($agent['id'], ENT_QUOTES);
                                $agentAppId = $agent['app_id'] ?? 'all';
                                $agentAppName = $agentAppId === 'all'
                                    ? '通用'
                                    : ($applicationsById[$agentAppId]['name'] ?? $agentAppId);
                            ?>
                            <tr>
                                <td><?php echo htmlspecialchars($agent['username']); ?></td>
                                <td><?php echo (int) ($agent['points'] ?? 0); ?></td>
                                <td><?php echo htmlspecialchars($agentAppName); ?></td>
                                <td><?php echo $agent['created_at'] ?? '-'; ?></td>
                                <td class="actions">
                                    <button onclick="editAgent('<?php echo $agentIdEsc; ?>','<?php echo htmlspecialchars($agent['username'], ENT_QUOTES); ?>','<?php echo (int) ($agent['points'] ?? 0); ?>','<?php echo htmlspecialchars($agentAppId, ENT_QUOTES); ?>')">编辑</button>
                                    <button class="danger" onclick="deleteAgent('<?php echo $agentIdEsc; ?>')">删除</button>
                                </td>
                            </tr>
                            <?php endforeach; ?>
                        <?php endif; ?>
                    </tbody>
                </table>
            </div>
        </div>
    </div>
    <div class="tab-content" id="api">
        <div class="api-doc">
            <h2>API 文档（全部内容可滚动查看）</h2>
            <div class="api-block">
                <strong>POST ?api=verify</strong>
                <p>验证并自动激活卡密，需传 <code>app_id</code>（卡所属应用，<code>app_general</code> 表示通用），超出多开限制会踢掉最久未心跳设备。</p>
<pre>{
  "card_key": "ABCD1234",
  "device_id": "device_xxx",
  "device_info": "Android_12",
  "app_id": "app_myapp"
}</pre>
            </div>
            <div class="api-block">
                <strong>POST ?api=login</strong>
                <p>验证已激活卡密并登录设备，同样需要传 <code>app_id</code>。</p>
                <strong>POST ?api=heartbeat</strong>
                <p>心跳维持在线状态，若设备被踢会收到 407。</p>
                <strong>POST ?api=logout</strong>
                <p>设备退出。</p>
            </div>
            <div class="api-block">
                <strong>POST ?api=trial</strong>
                <p>创建或查询单设备试用会话（默认 <?php echo getTrialDurationSeconds(); ?> 秒，可传 <code>duration</code> 控制，最大 86400 秒）。</p>
<pre>{
  "device_id": "trial_device_001",
  "duration": 1800
}</pre>
                <p>一个设备只允许一次试用，会话结束后再次调用会返回 409。</p>
            </div>
            <div class="api-block">
                <strong>POST ?api=notifications</strong>
                <p>获取当前登录用户的通知列表；<code>mark_notification_read</code> 用于标记已读。</p>
<pre>// mark_notification_read 请求体
{
  "notification_id": "notif_xxx"
}</pre>
                <strong>GET ?health</strong>
                <p>返回系统状态监控数据，便于外部健康检查。</p>
            </div>
            <div class="api-block">
                <strong>错误码</strong>
<pre>200 成功
401 参数错误
402 卡密不存在
403 禁用或无效
405 卡密过期
406 未登录
407 设备被踢</pre>
            </div>
        </div>
    </div>
    <?php endif; ?>
</div>
<form id="actionForm" method="POST" style="display:none;">
    <input type="hidden" name="action" value="">
    <input type="hidden" name="card_id" value="">
    <input type="hidden" name="extra" value="">
</form>
<form id="exportForm" method="GET" style="display:none;">
    <input type="hidden" name="export" value="cards">
    <input type="hidden" name="format" value="csv">
    <input type="hidden" name="ids" value="">
</form>
<form id="appForm" method="POST" style="display:none;">
    <input type="hidden" name="action" value="">
    <input type="hidden" name="app_id" value="">
    <input type="hidden" name="app_name" value="">
    <input type="hidden" name="app_description" value="">
</form>
<form id="agentForm" method="POST" style="display:none;">
    <input type="hidden" name="action" value="">
    <input type="hidden" name="agent_id" value="">
    <input type="hidden" name="username" value="">
    <input type="hidden" name="password" value="">
    <input type="hidden" name="points" value="">
    <input type="hidden" name="app_id" value="">
</form>
<script>
    const appOptions = [...<?php echo json_encode(array_map(function ($app) {
        return ['id' => $app['id'], 'name' => $app['name']];
    }, $applications), JSON_UNESCAPED_UNICODE); ?>, {id: 'all', name: '通用(全部)'}];
    const appOptionsList = appOptions.map(opt => `${opt.id}: ${opt.name}`).join('\n');
    const tabs = document.querySelectorAll('.tab');
    const contents = document.querySelectorAll('.tab-content');
    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            tabs.forEach(t => t.classList.remove('active'));
            contents.forEach(c => c.classList.remove('active'));
            tab.classList.add('active');
            const target = document.getElementById(tab.dataset.tab);
            if (target) target.classList.add('active');
            const params = new URLSearchParams(window.location.search);
            params.set('tab', tab.dataset.tab);
            const query = params.toString();
            const newUrl = query ? `${window.location.pathname}?${query}` : window.location.pathname;
            history.replaceState({}, '', newUrl);
        });
    });
    const initialTab = new URLSearchParams(window.location.search).get('tab');
    if (initialTab) {
        const initialEl = document.querySelector(`.tab[data-tab="${initialTab}"]`);
        if (initialEl) {
            initialEl.click();
        }
    }
    function submitAction(action, id, extra = '') {
        const form = document.getElementById('actionForm');
        form.action.value = action;
        form.card_id.value = id;
        form.extra.value = extra;
        form.submit();
    }
    function confirmDelete(id) {
        if (confirm('确定删除该卡密吗？')) {
            submitAction('delete_card', id);
        }
    }
    function copyKey(key) {
        navigator.clipboard.writeText(key).then(() => {
            alert('卡密已复制: ' + key);
        });
    }
    function promptNotes(id, current) {
        const value = prompt('输入备注（留空则清空）', current);
        if (value !== null) {
            submitAction('add_notes', id, value);
        }
    }
    function promptMax(id, current) {
        const value = prompt('设置多开数量 (1-10)', current);
        if (value !== null) {
            submitAction('update_max_devices', id, value);
        }
    }
    function promptDays(id) {
        const value = prompt('输入要增减的天数，正数增加，负数减少', '1');
        if (value !== null && value !== '') {
            submitAction('adjust_days', id, value);
        }
    }
    function goPage(page) {
        const params = new URLSearchParams(window.location.search);
        params.set('page', page);
        window.location.search = params.toString();
    }
    const rowCheckboxes = Array.from(document.querySelectorAll('.row-check'));
    const bulkBar = document.getElementById('bulkActions');
    const bulkCount = document.getElementById('bulkCount');
    const selectAll = document.getElementById('selectAll');

    function getSelectedIds() {
        return rowCheckboxes.filter(cb => cb.checked).map(cb => cb.value);
    }

    function updateBulkBar() {
        const ids = getSelectedIds();
        if (ids.length > 0) {
            if (bulkBar) bulkBar.classList.add('active');
            if (bulkCount) {
                bulkCount.textContent = ids.length;
            }
        } else {
            if (bulkBar) bulkBar.classList.remove('active');
            if (bulkCount) bulkCount.textContent = '0';
            if (selectAll) selectAll.checked = false;
        }
    }

    rowCheckboxes.forEach(cb => cb.addEventListener('change', updateBulkBar));

    if (selectAll) {
        selectAll.addEventListener('change', () => {
            rowCheckboxes.forEach(cb => {
                cb.checked = selectAll.checked;
            });
            updateBulkBar();
        });
    }

    function batchDeleteSelected() {
        const ids = getSelectedIds();
        if (!ids.length) {
            alert('请先选择要删除的卡密');
            return;
        }
        if (!confirm(`确定删除选中的 ${ids.length} 个卡密吗？`)) {
            return;
        }
        submitAction('batch_delete', '', ids.join(','));
    }

    function batchExportSelected() {
        const ids = getSelectedIds();
        if (!ids.length) {
            alert('请先选择要导出的卡密');
            return;
        }
        const form = document.getElementById('exportForm');
        if (!form) return;
        form.querySelector('input[name="ids"]').value = ids.join(',');
        form.submit();
    }

    function submitAgent(action, payload = {}) {
        const form = document.getElementById('agentForm');
        if (!form) return;
        form.querySelector('input[name="action"]').value = action;
        form.querySelector('input[name="agent_id"]').value = payload.agent_id || '';
        form.querySelector('input[name="username"]').value = payload.username || '';
        form.querySelector('input[name="password"]').value = payload.password || '';
        form.querySelector('input[name="points"]').value = Object.prototype.hasOwnProperty.call(payload, 'points') ? payload.points : '';
        form.querySelector('input[name="app_id"]').value = payload.app_id || '';
        form.submit();
    }
    function editAgent(id, username, points, appId) {
        const inputPoints = prompt('输入新的积分值', points);
        if (inputPoints === null) return;
        const normalized = String(inputPoints).trim();
        if (normalized === '' || isNaN(normalized)) {
            alert('请输入有效的积分数值');
            return;
        }
        const newPassword = prompt('输入新密码（可留空）', '');
        const newApp = prompt('输入新的应用ID（all = 通用）\n' + appOptionsList, appId || 'all');
        if (newApp === null) return;
        submitAgent('edit_agent', {
            agent_id: id,
            username,
            points: normalized,
            password: newPassword ? newPassword.trim() : '',
            app_id: newApp.trim()
        });
    }
    function deleteAgent(id) {
        if (!confirm('确定要删除该代理吗？')) return;
        submitAgent('delete_agent', { agent_id: id });
    }
    function deleteApp(appId) {
        if (!confirm('确定要删除该应用吗？')) return;
        const form = document.getElementById('appForm');
        if (!form) return;
        form.querySelector('input[name="action"]').value = 'delete_app';
        form.querySelector('input[name="app_id"]').value = appId;
        form.submit();
    }
</script>
</body>
</html>
