# Project conventions

Use Northstar Telecom as the fictional operator everywhere, including data and exports. Do not add real operator names or internal network information.

Focus the first lab on hosted Jev, a local trained ML classifier and a transparent rules reference. Do not download language-model weights or introduce other model providers without a new request.

Keep input packets and answer keys separate. Both Jev and ML inference must use the same allowlisted state string. Fit ML features and classifiers only on the training split. Do not tune against test or challenge labels.

Show actual predictions separately from reference decisions. Never fill missing model results with fabricated scores. Label synthetic results and keep them distinct from operational evidence.

API keys remain server-side, out of Git, logs and exported results. The app binds to loopback. Nothing in the lab executes network changes.

Run dataset validation, the unit suite and JavaScript syntax checks after changes to inference or evaluation. Update the learning guide when the workflow changes.
