#include "traitementdialog.h"

TraitementDialog::TraitementDialog(Traitement &t, QWidget *parent)
    : QDialog(parent), m_traitement(t)
{
    QFormLayout *layout = new QFormLayout(this);


    bandBox = new QComboBox(this);
    bandBox->addItems({"ndvi", "ndre"});
    bandBox->setCurrentText(t.band_detection);

    rectBox = new QComboBox(this);
    rectBox->addItems({"point", "rectangle"});
    rectBox->setCurrentText(t.similarities_rectangle);

    topPctDetection = new QLineEdit(t.top_pct_detection);
    minAreaDetection = new QLineEdit(t.min_area_detection);
    topPctTexture = new QLineEdit(t.top_pct_texture);
    minAreaTexture = new QLineEdit(t.min_area_texture);
    xSimilarities = new QLineEdit(t.x_similarities);
    ySimilarities = new QLineEdit(t.y_similarities);
    wSimilarities = new QLineEdit(t.w_similarities);
    hSimilarities = new QLineEdit(t.h_similarities);
    radiusSimilarities = new QLineEdit(t.radius_similarities);
    topkSimilarities = new QLineEdit(t.topk_similarities);

    layout->addRow("Band:", bandBox);

    layout->addRow("Top % Detection:", topPctDetection);
    layout->addRow("Min Area Detection:", minAreaDetection);
    layout->addRow("zones similaires:", rectBox);
    layout->addRow("Top % Texture:", topPctTexture);
    layout->addRow("Min Area Texture:", minAreaTexture);
    layout->addRow("X Similarities:", xSimilarities);
    layout->addRow("Y Similarities:", ySimilarities);

    layout->addRow("W Similarities:", wSimilarities);
    layout->addRow("H Similarities:", hSimilarities);

    layout->addRow("Radius:", radiusSimilarities);
    layout->addRow("TopK:", topkSimilarities);

    QDialogButtonBox *buttons = new QDialogButtonBox(
        QDialogButtonBox::Ok | QDialogButtonBox::Cancel, this);

    connect(buttons, &QDialogButtonBox::accepted, this, &TraitementDialog::accept);
    connect(buttons, &QDialogButtonBox::rejected, this, &TraitementDialog::reject);

    layout->addWidget(buttons);
}

void TraitementDialog::accept()
{
    m_traitement.band_detection = bandBox->currentText();
    m_traitement.top_pct_detection = topPctDetection->text();
    m_traitement.min_area_detection = minAreaDetection->text();
    m_traitement.top_pct_texture = topPctTexture->text();
    m_traitement.min_area_texture = minAreaTexture->text();
    m_traitement.x_similarities = xSimilarities->text();
    m_traitement.y_similarities = ySimilarities->text();
    m_traitement.radius_similarities = radiusSimilarities->text();
    m_traitement.topk_similarities = topkSimilarities->text();
    m_traitement.h_similarities = hSimilarities->text();
    m_traitement.w_similarities = wSimilarities->text();
    m_traitement.similarities_rectangle = rectBox->currentText();



    QDialog::accept();
}
