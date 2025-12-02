<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>卡密管理系统 - 登录</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * { box-sizing: border-box; }
        body {
            margin: 0;
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            font-family: 'Segoe UI', 'PingFang SC', sans-serif;
            background: linear-gradient(135deg, #667eea, #764ba2);
        }
        .card {
            width: 360px;
            background: rgba(255,255,255,0.95);
            border-radius: 16px;
            padding: 32px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.2);
        }
        h1 { text-align: center; margin-bottom: 24px; color: #333; }
        label { display: block; font-size: 14px; margin-bottom: 6px; color: #555; }
        input, select {
            width: 100%;
            padding: 12px;
            border-radius: 8px;
            border: 1px solid #dcdcdc;
            margin-bottom: 16px;
            font-size: 14px;
        }
        button {
            width: 100%;
            padding: 12px;
            border: none;
            border-radius: 8px;
            background: linear-gradient(135deg, #667eea, #764ba2);
            color: #fff;
            font-size: 16px;
            cursor: pointer;
        }
        .tabs { display: flex; gap: 12px; margin-bottom: 16px; }
        .tab {
            flex: 1;
            text-align: center;
            padding: 10px 0;
            border-radius: 8px;
            border: 1px solid #dcdcdc;
            cursor: pointer;
            font-weight: 600;
            color: #555;
        }
        .tab.active { border-color: #667eea; color: #667eea; }
        .alert {
            background: #fdecea;
            color: #c62828;
            padding: 10px 14px;
            border-radius: 8px;
            margin-bottom: 16px;
            font-size: 13px;
            text-align: center;
        }
    </style>
</head>
<body>
<div class="card">
    <h1>🔐 卡密系统</h1>
    <?php if (isset($_SESSION['error'])): ?>
        <div class="alert"><?php echo htmlspecialchars($_SESSION['error']); unset($_SESSION['error']); ?></div>
    <?php endif; ?>
    <div class="tabs">
        <div class="tab active" data-type="admin">管理员</div>
        <div class="tab" data-type="agent">代理</div>
    </div>
    <form method="POST" id="loginForm">
        <input type="hidden" name="action" value="login">
        <input type="hidden" name="user_type" id="userType" value="admin">
        <label for="username">用户名</label>
        <input type="text" id="username" name="username" required>
        <label for="password">密码</label>
        <input type="password" id="password" name="password" required>
        <button type="submit">登录</button>
    </form>
</div>
<script>
    const tabs = document.querySelectorAll('.tab');
    const userTypeInput = document.getElementById('userType');
    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            tabs.forEach(t => t.classList.remove('active'));
            tab.classList.add('active');
            userTypeInput.value = tab.dataset.type;
        });
    });
</script>
</body>
</html>
