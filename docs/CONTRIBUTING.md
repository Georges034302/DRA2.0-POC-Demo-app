# Contribution Policy

This proprietary proof of concept is not open to external contributions. Unsolicited pull requests and code submissions are not accepted. It is a demonstration, not a production-ready product or an open-source collaboration project.

Public visibility does not grant permission to copy, modify, test, deploy, or reuse this project. Any separately authorized work requires prior written permission from the copyright holder through an authorized channel and remains subject to the [license](../LICENSE).

## AI-Broker Scope

This repository contains the demo application and the CI/CD workflows that invoke AI-Broker. The private broker is maintained separately; its source and package access are not provided by this repository.

AI-Broker reviews selected evidence using Gemini or Groq and returns policy outcomes. The consuming workflows enforce approval and deployment gates; the broker does not build, deploy, modify code, or roll back the application.

Never include credentials, tokens, personal data, sensitive evidence, or private broker source in public issues or other public communications.

[Documentation index](index.MD)