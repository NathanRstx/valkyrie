#ifndef SCRIPTMANAGER_H
#define SCRIPTMANAGER_H

#include <QObject>
#include <QProcess>
#include <QStringList>

class ScriptManager : public QObject
{
    Q_OBJECT
public:
    ScriptManager(QObject *parent = nullptr);
    void runScript(const QString &scriptPath, const QStringList &args);
    void runCommand(const QString &program, const QStringList &args);

signals:
    void logMessage(const QString &message);
    void processFinished(bool success);
    void processStarted();

private slots:
    void handleProcessOutput();
    void handleProcessError();
    void handleProcessFinished(int exitCode, QProcess::ExitStatus exitStatus);

private:
    QProcess *m_process;
};

#endif // SCRIPTMANAGER_H
