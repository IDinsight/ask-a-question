# GitHub Actions — Android

GitHub Actions workflow patterns for Android projects using Kotlin, Jetpack Compose, and Gradle. Load this reference after the main CI/CD skill has confirmed the stack and target level.

## Runtime Setup

```yaml
- uses: actions/checkout@v4
- uses: actions/setup-java@v4
  with:
    distribution: 'temurin'
    java-version: '17'
- uses: gradle/actions/setup-gradle@v4
```

The `setup-gradle` action handles caching Gradle distributions, dependencies, and build outputs automatically. Do not add a separate cache step for Gradle.

---

## Level 1 — Lint + Unit Test

```yaml
name: CI
on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  lint:
    runs-on: ubuntu-latest
    timeout-minutes: 15
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-java@v4
        with:
          distribution: 'temurin'
          java-version: '17'
      - uses: gradle/actions/setup-gradle@v4
      - run: ./gradlew lint

  test:
    runs-on: ubuntu-latest
    timeout-minutes: 15
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-java@v4
        with:
          distribution: 'temurin'
          java-version: '17'
      - uses: gradle/actions/setup-gradle@v4
      - run: ./gradlew testDebugUnitTest
```

---

## Level 2 — Add Build + Detekt

```yaml
  detekt:
    runs-on: ubuntu-latest
    timeout-minutes: 10
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-java@v4
        with:
          distribution: 'temurin'
          java-version: '17'
      - uses: gradle/actions/setup-gradle@v4
      - run: ./gradlew detekt

  build:
    runs-on: ubuntu-latest
    timeout-minutes: 20
    needs: [lint, detekt, test]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-java@v4
        with:
          distribution: 'temurin'
          java-version: '17'
      - uses: gradle/actions/setup-gradle@v4
      - run: ./gradlew assembleDebug
      - uses: actions/upload-artifact@v4
        with:
          name: debug-apk
          path: app/build/outputs/apk/debug/app-debug.apk
          retention-days: 7
```

If the project doesn't use Detekt, substitute with `./gradlew ktlintCheck` or whatever static analysis the project has configured.

---

## Level 3 — Security Scan + Coverage + Signing

### Test with coverage

```yaml
  test:
    runs-on: ubuntu-latest
    timeout-minutes: 15
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-java@v4
        with:
          distribution: 'temurin'
          java-version: '17'
      - uses: gradle/actions/setup-gradle@v4
      - run: ./gradlew testDebugUnitTest koverXmlReportDebug
      - uses: actions/upload-artifact@v4
        if: always()
        with:
          name: coverage-report
          path: app/build/reports/kover/
          retention-days: 7
```

Uses Kover for Kotlin coverage. If the project uses JaCoCo instead, replace with `./gradlew jacocoTestReport`.

### Dependency vulnerability scan

```yaml
  security:
    runs-on: ubuntu-latest
    timeout-minutes: 10
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-java@v4
        with:
          distribution: 'temurin'
          java-version: '17'
      - uses: gradle/actions/setup-gradle@v4
      - run: ./gradlew dependencyCheckAnalyze
```

Requires the `org.owasp.dependencycheck` Gradle plugin. If not present, use GitHub's Dependabot instead (see Level 5 section).

### Signed release build

```yaml
  build-release:
    runs-on: ubuntu-latest
    timeout-minutes: 25
    needs: [lint, detekt, test]
    if: github.ref == 'refs/heads/main' && github.event_name == 'push'
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-java@v4
        with:
          distribution: 'temurin'
          java-version: '17'
      - uses: gradle/actions/setup-gradle@v4
      - name: Decode keystore
        run: echo "${{ secrets.KEYSTORE_BASE64 }}" | base64 -d > app/release.keystore
      - run: ./gradlew assembleRelease
        env:
          KEYSTORE_PASSWORD: ${{ secrets.KEYSTORE_PASSWORD }}
          KEY_ALIAS: ${{ secrets.KEY_ALIAS }}
          KEY_PASSWORD: ${{ secrets.KEY_PASSWORD }}
      - uses: actions/upload-artifact@v4
        with:
          name: release-apk
          path: app/build/outputs/apk/release/app-release.apk
          retention-days: 30
```

The keystore is stored as a base64-encoded repository secret. Decode it at build time — never commit it to the repository.

### Concurrency and permissions (Level 3+)

```yaml
permissions:
  contents: read

concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true
```

---

## Level 4 — Firebase App Distribution + Notifications

### Build and distribute via Firebase App Distribution

For beta testing and pre-release QA, use Firebase App Distribution to get your APK or AAB to testers without Play Store deployment:

```yaml
  build-release:
    runs-on: ubuntu-latest
    timeout-minutes: 25
    needs: [lint, detekt, test]
    if: github.ref == 'refs/heads/main' && github.event_name == 'push'
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-java@v4
        with:
          distribution: 'temurin'
          java-version: '17'
      - uses: gradle/actions/setup-gradle@v4
      - name: Decode keystore
        run: echo "${{ secrets.KEYSTORE_BASE64 }}" | base64 -d > app/release.keystore
      - run: ./gradlew assembleRelease
        env:
          KEYSTORE_PASSWORD: ${{ secrets.KEYSTORE_PASSWORD }}
          KEY_ALIAS: ${{ secrets.KEY_ALIAS }}
          KEY_PASSWORD: ${{ secrets.KEY_PASSWORD }}
      - uses: actions/upload-artifact@v4
        with:
          name: release-apk
          path: app/build/outputs/apk/release/app-release.apk
          retention-days: 7

  distribute-firebase:
    runs-on: ubuntu-latest
    timeout-minutes: 10
    needs: [build-release]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/download-artifact@v4
        with:
          name: release-apk
      - uses: actions/setup-python@v5
      - name: Install Firebase CLI
        run: npm install -g firebase-tools
      - name: Distribute via Firebase App Distribution
        env:
          FIREBASE_TOKEN: ${{ secrets.FIREBASE_TOKEN }}
        run: |
          firebase appdistribution:distribute app-release.apk \
            --app="${{ secrets.FIREBASE_APP_ID }}" \
            --release-notes="Build ${{ github.run_number }} from commit ${{ github.sha }}" \
            --groups="qa-testers"
```

For Firebase CLI setup: Generate a CI token with `firebase login:ci` and store it as `FIREBASE_TOKEN` in repository secrets. See [Firebase CLI reference: Using the CLI with CI systems](https://firebase.google.com/docs/cli#use_the_cli_with_ci_systems).

### Slack notification on failure

```yaml
  notify:
    runs-on: ubuntu-latest
    timeout-minutes: 5
    needs: [lint, detekt, test, build-release]
    if: failure() && github.ref == 'refs/heads/main'
    steps:
      - uses: slackapi/slack-github-action@v2
        with:
          webhook: ${{ secrets.SLACK_WEBHOOK_URL }}
          webhook-type: incoming-webhook
          payload: |
            {
              "text": "Android CI failed on main: ${{ github.server_url }}/${{ github.repository }}/actions/runs/${{ github.run_id }}"
            }
```

### Slack notification on failure

```yaml
  notify:
    runs-on: ubuntu-latest
    timeout-minutes: 5
    needs: [lint, detekt, test, build]
    if: failure() && github.ref == 'refs/heads/main'
    steps:
      - uses: slackapi/slack-github-action@v2
        with:
          webhook: ${{ secrets.SLACK_WEBHOOK_URL }}
          webhook-type: incoming-webhook
          payload: |
            {
              "text": "Android CI failed on main: ${{ github.server_url }}/${{ github.repository }}/actions/runs/${{ github.run_id }}"
            }
```

---

## Level 5 — Pin Actions + Play Store Production Release

### Build AAB and upload to Play Store

For production releases, build an AAB and upload to Play Store after Firebase testing is complete:

```yaml
  build-aab:
    runs-on: ubuntu-latest
    timeout-minutes: 25
    needs: [lint, detekt, test]
    if: github.event_name == 'release'
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-java@v4
        with:
          distribution: 'temurin'
          java-version: '17'
      - uses: gradle/actions/setup-gradle@v4
      - name: Decode keystore
        run: echo "${{ secrets.KEYSTORE_BASE64 }}" | base64 -d > app/release.keystore
      - run: ./gradlew bundleRelease
        env:
          KEYSTORE_PASSWORD: ${{ secrets.KEYSTORE_PASSWORD }}
          KEY_ALIAS: ${{ secrets.KEY_ALIAS }}
          KEY_PASSWORD: ${{ secrets.KEY_PASSWORD }}
      - uses: actions/upload-artifact@v4
        with:
          name: release-aab
          path: app/build/outputs/bundle/release/app-release.aab
          retention-days: 7

  deploy-play-store:
    runs-on: ubuntu-latest
    timeout-minutes: 15
    needs: [build-aab]
    environment: play-store
    steps:
      - uses: actions/download-artifact@v4
        with:
          name: release-aab
      - uses: r0adkll/upload-google-play@v1
        with:
          serviceAccountJsonPlainText: ${{ secrets.PLAY_STORE_SERVICE_ACCOUNT }}
          packageName: com.example.app
          releaseFiles: app-release.aab
          track: internal
```

### Dependabot

```yaml
# .github/dependabot.yml
version: 2
updates:
  - package-ecosystem: "gradle"
    directory: "/"
    schedule:
      interval: "weekly"
    open-pull-requests-limit: 5

  - package-ecosystem: "github-actions"
    directory: "/"
    schedule:
      interval: "weekly"
```

---

## Instrumented Tests (Optional)

Instrumented tests (Espresso, Compose UI tests) require an Android emulator. These are slow and flaky in CI — run them only when explicitly needed.

```yaml
  instrumented-test:
    runs-on: ubuntu-latest
    timeout-minutes: 30
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-java@v4
        with:
          distribution: 'temurin'
          java-version: '17'
      - uses: gradle/actions/setup-gradle@v4
      - name: Enable KVM
        run: |
          echo 'KERNEL=="kvm", GROUP="kvm", MODE="0666", OPTIONS+="static_node=kvm"' | sudo tee /etc/udev/rules.d/99-kvm4all.rules
          sudo udevadm control --reload-rules
          sudo udevadm trigger --name-match=kvm
      - uses: reactivecircus/android-emulator-runner@v2
        with:
          api-level: 34
          arch: x86_64
          script: ./gradlew connectedDebugAndroidTest
```

KVM acceleration is required for acceptable emulator performance on GitHub-hosted runners. Without the KVM setup step, tests will be extremely slow or timeout.

---

## Common Pitfalls

- **Missing `chmod +x gradlew`.** The Gradle wrapper script must be executable. If it's not (common after a Windows commit), add `chmod +x gradlew` before the first Gradle command, or fix the file permissions in the repository.
- **Gradle daemon memory.** CI should not reuse daemons across builds. `setup-gradle` handles this, but if using raw Gradle, pass `--no-daemon` to avoid OOM issues.
- **Keystore in the repository.** Never commit the signing keystore. Store it as a base64-encoded secret and decode it at build time. Clean it up after the build if the workflow continues with other steps.
- **Emulator flakiness.** Android emulator tests are inherently flaky in CI. Set `fail-fast: false` on matrix builds, increase timeouts, and consider running instrumented tests only on merge to main (not on every PR).
- **Large APK/AAB artifacts.** Set `retention-days` to avoid accumulating stale build artifacts. Release artifacts should be retained longer (30 days) than debug artifacts (7 days).

---

## Authoritative References

- [GitHub Actions workflow syntax](https://docs.github.com/en/actions/using-workflows/workflow-syntax-for-github-actions)
- [actions/setup-java](https://github.com/actions/setup-java)
- [gradle/actions/setup-gradle](https://github.com/gradle/actions)
- [reactivecircus/android-emulator-runner](https://github.com/ReactiveCircus/android-emulator-runner)
- [r0adkll/upload-google-play](https://github.com/r0adkll/upload-google-play)
- [Firebase CLI — CI systems](https://firebase.google.com/docs/cli)
- [Firebase App Distribution](https://firebase.google.com/docs/app-distribution)
- [Dependabot configuration](https://docs.github.com/en/code-security/dependabot/working-with-dependabot/keeping-your-actions-up-to-date-with-dependabot)
- [Kover — Kotlin code coverage](https://github.com/Kotlin/kotlinx-kover)
- [Detekt — Kotlin static analysis](https://detekt.dev/docs/intro/)
