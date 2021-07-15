#!/bin/bash

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

pyinstaller --onefile --windowed $DIR/../creditorGUI.py --distpath  $DIR/../bin --workpath $DIR/build --specpath $DIR/build --add-data $DIR/../common/green.png:common/ --add-data $DIR/../common/red.png:common/ --add-data $DIR/../common/ui/balancewidget.ui:common/ui/ --add-data $DIR/../common/ui/plansummary.ui:common/ui/ --add-data $DIR/../creditor/ui/mainwindow.ui:creditor/ui/  --add-data $DIR/../creditor/ui/createplandialog.ui:creditor/ui/

pyinstaller --onefile --windowed $DIR/../debtorGUI.py --distpath  $DIR/../bin --workpath $DIR/build --specpath $DIR/build  --add-data $DIR/../common/green.png:common/ --add-data $DIR/../common/red.png:common/ --add-data $DIR/../common/ui/balancewidget.ui:common/ui/ --add-data $DIR/../common/ui/plansummary.ui:common/ui/ --add-data $DIR/../debtor/ui/mainwindow.ui:debtor/ui/

pyinstaller --onefile --windowed $DIR/../facilitatorGUI.py --distpath  $DIR/../bin --workpath $DIR/build --specpath $DIR/build --add-data $DIR/../facilitator/ui/mainwindow.ui:facilitator/ui/

pyinstaller --onefile --windowed $DIR/../minerGUI.py --distpath  $DIR/../bin --workpath $DIR/build --specpath $DIR/build --add-data $DIR/../miner/ui/mainwindow.ui:miner/ui/

pyinstaller --onefile $DIR/../cli/creditor_cli.py --distpath  $DIR/../bin/cli --workpath $DIR/build --specpath $DIR/build

pyinstaller --onefile $DIR/../cli/debtor_cli.py --distpath  $DIR/../bin/cli --workpath $DIR/build --specpath $DIR/build

pyinstaller --onefile $DIR/../cli/facilitator_cli.py --distpath  $DIR/../bin/cli --workpath $DIR/build --specpath $DIR/build

