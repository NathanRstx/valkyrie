#ifndef TRAITEMENTDIALOG_H
#define TRAITEMENTDIALOG_H

#include <QDialog>
#include <QLineEdit>
#include <QComboBox>
#include <QFormLayout>
#include <QDialogButtonBox>
#include "traitement.h"

class TraitementDialog : public QDialog
{
    Q_OBJECT

public:
    explicit TraitementDialog(Traitement &t, QWidget *parent = nullptr);

private:
    Traitement &m_traitement;

    QComboBox *bandBox;
    QComboBox *rectBox;
    QLineEdit *topPctDetection;
    QLineEdit *minAreaDetection;
    QLineEdit *topPctTexture;
    QLineEdit *minAreaTexture;
    QLineEdit *xSimilarities;
    QLineEdit *ySimilarities;
    QLineEdit *wSimilarities;
    QLineEdit *hSimilarities;

    QLineEdit *radiusSimilarities;
    QLineEdit *topkSimilarities;

private slots:
    void accept() override;
};

#endif
