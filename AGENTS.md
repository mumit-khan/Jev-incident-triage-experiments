# Project conventions

Use Northstar Telecom as the fictional operator everywhere, including data and exports. Do not add real operator names or internal network information.

Focus the first lab on hosted Jev, a local trained ML classifier and a transparent rules reference. Do not download language-model weights or introduce other model providers without a new request.

Keep input packets and answer keys separate. Original Jev/ML share the original allowlisted state string; focused Jev/revised ML share the compact allowlisted state string. Fit ML features and classifiers only on the training split. Do not tune against test or challenge labels.

Show actual predictions separately from reference decisions. Never fill missing model results with fabricated scores. Label synthetic results and keep them distinct from operational evidence.

API keys remain server-side, out of Git, logs and exported results. The app binds to loopback. Nothing in the lab executes network changes.

Run dataset validation, the unit suite and JavaScript syntax checks after changes to inference or evaluation. Update the learning guide when the workflow changes.

Use the app labels Rules, ML · original, ML · revised, Jev · original and Jev · focused in guides. Keep the user-edited experiment overview and exported Markdown copies aligned. Preserve frozen data and measured results; raw runs and credentials stay ignored. Run the Python suite, dataset validator, both browser-script syntax checks and `node --test tests/explorer-ui.test.cjs` before publishing changes.

Write study narration in first person for authorship, choices, judgments and limitations. Let models, data, methods and results lead descriptions of their behavior. Avoid repeated “I used,” “I trained” or “I will” openings. Preserve completed-versus-planned work and technical qualifications when revising prose.
