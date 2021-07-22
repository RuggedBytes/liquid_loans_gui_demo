# The demo for "Asset-Based Lending smart contract for Liquid network"

This is the source code for the demo that accompanies the article at
[https://ruggedbytes.com/articles/ll/](https://ruggedbytes.com/articles/ll/) --
"Asset-Based Lending smart contract for Liquid network".

It includes the environment to run the demo. It can be build with `docker-compose`
according to the config in `docker-compose.yml`. The environment includes the
customised docker image for the [Esplora](https://github.com/Blockstream/esplora)
blockchain explorer, and the main docker image for the demo.

The code here is intended for demonstration and research purposes, and the environment
is set up to work with 'liquidregtest' network, which is not a real Liquid network.
It should be possible to run with real Liquid network by editing the configuration files
for the demo programs, but those who will do it should know that they are doing, and
that they are doing it at their own risk (risk for their funds). Thus, no attempt were made
to make it easier to use this with real live Liquid network.

The GUI part relies on the CLI tools that implement the workings of the contract
described in the article. These CLI tools are linked as a git submodule under
`cli` directory. The CLI tools source is available at
[https://github.com/RuggedBytes/liquid_loans_cli](https://github.com/RuggedBytes/liquid_loans_cli)

## Experimental code

At the moment of release, the code for the CLI tools have received more attention in
regards of the quality of code and testing; it passes mypy typechecking with --strict
option. It still have not been used in live Liquid network at the time of the release,
and is therefore its status should be considered an experimental code with all what this
implies.

The code for GUI demo received just enough attention and testing for it to be useable
to understand the concept of the contract described in the article and to study the way
the CLI tools are supposed to be used.

These GUI demo tools also lack the code for mutual-agreement contract close, although
the CLI tools implement this.

# How to run the demo

`git submodule init`

`git submodule update`

`docker-compose up liquid-loans-demo`

This was tested on Ubuntu 20.04 as the host system.
It is expected to be run in the graphical environment, since the config in
`docker-compose.yml` will be attaching the host's `/tmp/.X11-unix` and `/dev/dri`
directories into the docker container. This, along with passing the host's DISPLAY
environment variable, allows the GUI tools inside the container to run successfully.

There are probably a bunch of useless dependencies installed in the docker image,
and Elements daemon is compiled instead of just downloading the binaries.
It thus can take time to build the image, sorry about that.

Several mock assets are issued inside the 'liquidregtest' network that the Elements
daemons within the images run.

When the demo is run, four GUI programs are started:

- `creditorGUI.py` -- the interface for the 'Creditor' role
- `debtorGUI.py` -- the interface for the 'Debtor' role
- `facilitatorGUI.py` -- the interface for 'Facilitator' role
- `minerGUI.py` -- The helper tool to control block creation in the demo 'liquidregtest'
   network

When `minerGUI.py` is closed, the docker image `liquid-loans-demo` will stop (since this
is the last program that is invoked from the `gui_progs.sh` script)

## GUI demo programs

When the demo is run, you will see 4 windows of the GUI demo programs.

Creditor will use the wallet from the first Elements daemon, located at /root/elementsdir1
Debtor and Facilitator will use the wallet from the second Elements daemon,
located at /root/elementsdir2

The Miner control program simply allows you to start generating blocks with the selected
inter-block interval.

The Facilitator control will allow to do the role of the facilitator (described in the
article).
- "Create" function is for creating the contract transaction from the data
   supplied by the Debtor and Creditor
- "Sign" function is to update the transaction with the signatures from Debtor and Creditor,
  along with signing the input to pay the fee, which is done by the Facilitator (although
  in this demo environment, Facilitator will use the same wallet as Debtor)
- "Send" function will simply send the signed transaction to the network, even though
  this can be done by anyone after transaction is signed

The Debtor and Creditor will allow to perform the actions of the Debtor and Creditor roles
accordingly. The buttons available are self-descriptive for the actions to take. Note that
sometimes the button may be active even if the underlying function is not possible to be
performed. Adding the logic to always disable the buttons in appropriate context is the work
that has not been done, but this does not prevent the exploration of the contract execution
logic with the GUI tools, so please bear with that.

Debtor and Creditor window also show the balance for the mock assets and the "bitcoin" asset
(that is also not a real L-BTC since this is a regtest network). The names of these assets
are retrieved with `dumpassetlabels` rpc command from the respective Elements daemon. This
is the aggregate balance, but the CLI tools work in terms of individual UTXO. It is therefore
possible that at some point the tool might not find the UTXO with suitable amount, even if
balance is sufficient. There's no GUI tool to consolidate the coins, to do that, you'll need
to enter the liquid-loans-demo container and do everythin manually via elements-cli command
available at `/root/elements`. This requires experience with commandline and docker containers,
but this will be needed only after a lot of experimentation with the contract when the coins
will become fragmented, and it is always possible to go back to the initial state by rebuilding
the containers.

When particular collateral and principal assets are chosen, the Balance widget will only show
balance of those two assets.

The programs share information via files, where the file suffix is important. For example,
if the program is working with the loan plan "x.plan", it will create and look for the files
like "x.dinfo" (Debtor's info), "x.cinfo" (Creditor's info), "x.ddata", "x.cdata", "x.tx", etc.
It is therefore advised to create a directory to save the loan plans, so all these various
files will be under that directory. These files will reside inside the docker container.
You will need to run the shell inside the container to examine them, or you might mount the
project's directory as a volume within the container (add `- .:/app` to `volumes` for
`liquid-loans-demo` config in `docker-compose.yaml` and comment out `COPY ./ /app` in
the Dockerfile), then the files will be saved on the host, but the owner of the saved files will
be root.

The GUI programs print the commands for CLI tools they run on the terminal (this will be
the terminal where you've run `docker-compose up liquid-loans-demo`.

## The flow of the contract execution with GUI demo programs

First step is to create the loan plan. For this, click on "Create plan" on Creditor window.
There you will need to choose two assets and amounts for them, and also a bunch of other
parameters that are discussed in the article. When you're ok with the loan plan parameters,
click "OK". In the file dialog, create the "plans" directory, and name your plan. I will be
using the name "x", and after clicking Save, "plans/x.plan" and "plans/x.cinfo" will be created.
"x.cinfo" file ("Creditor's info") contains the information from the creditor for participating
in the contract, and this file will be used by Facilitator.

Click on "Open plan" in the Debtor window. Open "x.plan" from "plans" directory and
observe the resulting visualization of the plan. If the Debtor is OK with the plan, click
"Accept plan". "plans/x.dinfo" ("Debtor's info") will be created. This file will be used
by Facilitator along with "x.cinfo" to create the contract transaction.

Click on "Create" on the Facilitator window, and choose "x.plan". Choose the number of blocks
to wait for the contract to start, this will put the locktime on the contract transaction
so it will not be possible to broadcast it before the selected number of blocks are minded.
In the messagebox following after you click "OK", note the block number on which the transaction
will be allowed to be broadcasted. The transaction will be saved, in our case, into "plans/x.tx"
Along with it "plans/x.dinfo" and "plans/x.cinfo" files are created, which will be used by
Debtor and Creditor to form their signatures for the contract transaction.

Click on "Open contract data" in both Debtor and Creditor window, ans select "x.ddata" and
"x.cdata" accordingly. After that, click on "Sign contract transaction". This will result
in creating "plans/x.dsignature" and "plans/x.csignature". These files will be used by
Facilitator to create the signed contract transaction.

Click on "Sign" in Facilitator window and choose "x.tx". The Facilitator program will take
the name of the plan ("x") and will look for `{plan_name}.csignature` and
`{plan_name}.csignature`. It will save the signed transaction into `{plan_name}.stx` and
will also lock the UTXO for the fee in the wallet, announcing the txid:vout of this utxo
in the resulting messagebox.

Now go to Miner control window and click on "Generate blocks" checkbox to start generating
blocks. Wait for the block number you noted when performing the "Create" function of the
Facilitator.

After the target block is reached, click on "Send" and choose "x.stx". The contract transaction
will be broadcasted, and Creditor and Debtor windows should show a number of new information:

- The contract txid (the link that will open a browser to the Esplora instance for you to
  examine the transaction),
- The loan plan will show the current stage in green
- The "Window time" bar will indicate if the current period to repay the debt is ended or not.

When the period to repay the debt is ended, the "Window time" bar will turn red and Creditor
will be able to use "Revoke payment window" function to move thecontract state vertically.

Any time before the payment window is revoked, Debtor will be able to use "Regular payment"
to partially repay the debt, or "Early payment" to fully repay the debt. "Regular payment"
will move the contract state horizontally, and "Early payment" will finish the contract.

If your inter-block period is small, you'll probably want to stop the block generation after
performing an action, or you won't be able to perform the Debtor's payments in time.

After the payment was made, Creditor will be able to "Spend payment". This is needed because
the repayments made by the Debtor are not sent to the Creditor's wallet directly, but
to the special covenant that is controlled by "Creditor's control asset" (see the article
for details). "Spend payment" uses this control asset to send the funds to Creditor's wallet.

If the Debtor does not pay, the Creditor will be able to use "Grab collateral" function,
after the contract reaches the last vertical stage (note that red boxes do not represent
a contract stage, but just show the division of the collateral in case of Debtor's default).
You won't be able to "Grab collateral" if you did not spent the previously paid repayments
from the control-asset covenant to Creditor's wallet. If the "Spend payment" button is green,
spend those payments first, and then you can grab the collateral.

Note that while the CLI tools have a guard logic against grabbing collateral before unclaimed
repayments are spent, the smart contract itself does not prevent this. Grabbing the collateral
also destroys the control asset, and this control asset is needed to claim the repayments.
The guard logic on the application level prevents the situation where these repayments will
be stuck unclaimed forever. The issue is discussed in more detail in the
[https://ruggedbytes.com/articles/ll/#collateral-forfeiture]("Collateral forfeiture") section
of the Appendix in the article.

After Creditor grabs the collateral, the Debtor will be able to use "Get remaining collateral"
to receive its portion of the collateral after the other portion was grabbed by the Creditor.

After the contract is finished, you can click on the "Last contract txid" link to examine
the final transaction in Esplora.
