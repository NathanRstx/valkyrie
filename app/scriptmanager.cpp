#include "scriptmanager.h"

ScriptManager::ScriptManager(QObject *parent)
    : QObject(parent)
{
    m_process = new QProcess();
    connect(m_process,
            &QProcess::readyReadStandardOutput,
            this,
            &ScriptManager::handleProcessOutput);
    connect(m_process, &QProcess::readyReadStandardError, this, &ScriptManager::handleProcessError);
    connect(m_process,
            QOverload<int, QProcess::ExitStatus>::of(&QProcess::finished),
            this,
            &ScriptManager::handleProcessFinished);
}
void ScriptManager::runScript(const QString &scriptPath, const QStringList &args)
{
    if (m_process->state() != QProcess::NotRunning) {
        emit logMessage("Un traitement est déjà en cours");
        return;
    }
    emit logMessage("Lancement du script");
    emit processStarted();
    m_process->start("python3", QStringList() << scriptPath << args);
}
void ScriptManager::runCommand(const QString &program, const QStringList &args)
{
    if (m_process->state() != QProcess::NotRunning) {
        emit logMessage("Un traitement est déjà en cours");
        return;
    }
    emit logMessage("Lancement du script");
    emit processStarted();
    m_process->start(program, args);
}
void ScriptManager::handleProcessOutput()
{
    emit logMessage(m_process->readAllStandardOutput().trimmed());
}
void ScriptManager::handleProcessError()
{
    emit logMessage("ERROR " + m_process->readAllStandardError().trimmed());
}
void ScriptManager::handleProcessFinished(int exitCode, QProcess::ExitStatus exitStatus)
{
    bool success = (exitStatus == QProcess::NormalExit && exitCode == 0);
    if (success) {
        emit logMessage("Traitement terminé!");
    } else {
        emit logMessage("Échec du Traitement");
    }
    emit processFinished(success);
}
