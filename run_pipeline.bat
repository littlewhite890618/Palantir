@echo off
set LOG=C:\Users\evalu\Desktop\JOHNNY\n8ntest\subsidy_crawler\data\pipeline_run.log
echo ===== %date% %time% ===== >> "%LOG%"
cd /d C:\Users\evalu\Desktop\JOHNNY\n8ntest
python -m subsidy_crawler.pipeline >> "%LOG%" 2>&1
set RC=%errorlevel%
echo ===== exit code %RC% ===== >> "%LOG%"
exit /b %RC%
