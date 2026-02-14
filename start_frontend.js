const { spawn } = require('child_process');
const path = require('path');

const frontendDir = path.join('d:', 'workplace', 'adsagent', 'frontend');

console.log('启动前端服务...');
console.log('工作目录:', frontendDir);

const npm = spawn('npm', ['run', 'dev'], {
  cwd: frontendDir,
  shell: true,
  stdio: 'inherit'
});

npm.on('error', (error) => {
  console.error('启动失败:', error);
  process.exit(1);
});

npm.on('close', (code) => {
  console.log(`前端服务退出,代码: ${code}`);
});
