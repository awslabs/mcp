# AWS용 오픈 소스 MCP 서버

> 이 문서는 영문 원문 [README.md](README.md)의 한국어 번역입니다. 원문이 갱신된 이후에는 내용이 다를 수 있으므로, 최신 정보는 원문을 확인하세요.

MCP를 사용하는 모든 환경에서 AWS를 최대한 활용할 수 있도록 돕는 특화된 MCP 서버 모음입니다.

[![GitHub](https://img.shields.io/badge/github-awslabs/mcp-blue.svg?style=flat&logo=github)](https://github.com/awslabs/mcp)
[![License](https://img.shields.io/badge/license-Apache--2.0-brightgreen)](LICENSE)
[![Codecov](https://img.shields.io/codecov/c/github/awslabs/mcp)](https://app.codecov.io/gh/awslabs/mcp)
[![OSSF-Scorecard Score](https://img.shields.io/ossf-scorecard/github.com/awslabs/mcp)](https://scorecard.dev/viewer/?uri=github.com/awslabs/mcp)

> [!TIP]
> [Agent Toolkit for AWS](https://aws.amazon.com/about-aws/whats-new/2026/05/agent-toolkit/)가 출시되었습니다! Agent Toolkit for AWS는 AWS Labs에서 제공하던 MCP 서버, 플러그인, 스킬의 후속 제품으로, 여러분과 같은 고객의 피드백을 바탕으로 만들어졌습니다. 코딩 에이전트를 사용해 프로덕션 소프트웨어를 구축하거나 고객을 위한 에이전트를 개발하고 있다면 Agent Toolkit for AWS를 권장합니다. 에이전트의 작업과 사람의 작업을 구분하는 IAM 조건 키, CloudWatch 및 CloudTrail 가시성, 정확성과 효과성이 검증된 스킬을 포함합니다. 이 리포지토리는 계속 동작하며 기여도 받고 있습니다. 시간이 지나면서 이곳의 유용한 프로젝트들은 Agent Toolkit for AWS로 이전될 예정입니다.

## 목차

- [AWS용 오픈 소스 MCP 서버](#aws용-오픈-소스-mcp-서버)
  - [목차](#목차)
  - [Model Context Protocol(MCP)이란 무엇이며, AWS용 MCP 서버와 어떻게 함께 동작하나요?](#model-context-protocolmcp이란-무엇이며-aws용-mcp-서버와-어떻게-함께-동작하나요)
  - [AWS용 오픈 소스 MCP 서버의 전송 메커니즘](#aws용-오픈-소스-mcp-서버의-전송-메커니즘)
    - [지원되는 전송 메커니즘](#지원되는-전송-메커니즘)
    - [Server Sent Events(SSE) 지원 중단](#server-sent-eventssse-지원-중단)
    - [AWS용 MCP 서버가 필요한 이유](#aws용-mcp-서버가-필요한-이유)
  - [사용 가능한 MCP 서버: 빠른 설치](#사용-가능한-mcp-서버-빠른-설치)
    - [🚀 AWS 시작하기](#-aws-시작하기)
    - [구축 대상별로 살펴보기](#구축-대상별로-살펴보기)
      - [📚 공식 AWS 문서에 대한 실시간 접근](#-공식-aws-문서에-대한-실시간-접근)
    - [🏗️ 인프라 및 배포](#️-인프라-및-배포)
      - [컨테이너 플랫폼](#컨테이너-플랫폼)
      - [서버리스 및 함수](#서버리스-및-함수)
      - [마이그레이션 및 현대화](#마이그레이션-및-현대화)
      - [지원](#지원)
    - [🤖 AI 및 머신 러닝](#-ai-및-머신-러닝)
    - [📊 데이터 및 분석](#-데이터-및-분석)
      - [SQL 및 NoSQL 데이터베이스](#sql-및-nosql-데이터베이스)
        - [검색 및 분석](#검색-및-분석)
      - [백엔드 API 제공자](#백엔드-api-제공자)
      - [캐싱 및 성능](#캐싱-및-성능)
      - [오픈 데이터](#오픈-데이터)
    - [🛠️ 개발자 도구 및 지원](#️-개발자-도구-및-지원)
    - [📡 통합 및 메시징](#-통합-및-메시징)
    - [💰 비용 및 운영](#-비용-및-운영)
    - [🧬 헬스케어 및 생명과학](#-헬스케어-및-생명과학)
    - [작업 방식별로 살펴보기](#작업-방식별로-살펴보기)
      - [👨‍💻 바이브 코딩 및 개발](#-바이브-코딩-및-개발)
        - [핵심 개발 워크플로](#핵심-개발-워크플로)
        - [코드형 인프라(Infrastructure as Code)](#코드형-인프라infrastructure-as-code)
        - [애플리케이션 개발](#애플리케이션-개발)
        - [컨테이너 및 서버리스 개발](#컨테이너-및-서버리스-개발)
        - [테스트 및 데이터](#테스트-및-데이터)
        - [생명과학 워크플로 개발](#생명과학-워크플로-개발)
        - [헬스케어 데이터 관리](#헬스케어-데이터-관리)
      - [💬 대화형 어시스턴트](#-대화형-어시스턴트)
        - [지식 및 검색](#지식-및-검색)
        - [콘텐츠 처리 및 생성](#콘텐츠-처리-및-생성)
        - [비즈니스 서비스](#비즈니스-서비스)
      - [🤖 자율 백그라운드 에이전트](#-자율-백그라운드-에이전트)
        - [데이터 운영 및 ETL](#데이터-운영-및-etl)
        - [캐싱 및 성능](#캐싱-및-성능-1)
        - [워크플로 및 통합](#워크플로-및-통합)
        - [운영 및 모니터링](#운영-및-모니터링)
  - [MCP AWS Lambda 핸들러 모듈](#mcp-aws-lambda-핸들러-모듈)
  - [로컬 MCP 서버와 원격 MCP 서버는 각각 언제 사용하나요?](#로컬-mcp-서버와-원격-mcp-서버는-각각-언제-사용하나요)
    - [로컬 MCP 서버](#로컬-mcp-서버)
    - [원격 MCP 서버](#원격-mcp-서버)
  - [서버 활용 사례](#서버-활용-사례)
  - [설치 및 설정](#설치-및-설정)
    - [macOS/Linux용 설정](#macoslinux용-설정)
    - [Windows용 설정](#windows용-설정)
    - [컨테이너에서 MCP 서버 실행하기](#컨테이너에서-mcp-서버-실행하기)
    - [Kiro로 시작하기](#kiro로-시작하기)
      - [`~/.kiro/settings/mcp.json`](#kirosettingsmcpjson)
    - [Cline 및 Amazon Bedrock으로 시작하기](#cline-및-amazon-bedrock으로-시작하기)
      - [`cline_mcp_settings.json`](#cline_mcp_settingsjson)
    - [Cursor로 시작하기](#cursor로-시작하기)
      - [`.cursor/mcp.json`](#cursormcpjson)
    - [Windsurf로 시작하기](#windsurf로-시작하기)
      - [`~/.codeium/windsurf/mcp_config.json`](#codeiumwindsurfmcp_configjson)
    - [VS Code로 시작하기](#vs-code로-시작하기)
      - [`.vscode/mcp.json`](#vscodemcpjson)
    - [Claude Code로 시작하기](#claude-code로-시작하기)
      - [`.mcp.json`](#mcpjson)
  - [샘플](#샘플)
  - [바이브 코딩](#바이브-코딩)
  - [추가 리소스](#추가-리소스)
  - [보안](#보안)
  - [기여하기](#기여하기)
  - [개발자 가이드](#개발자-가이드)
  - [라이선스](#라이선스)
  - [면책 조항](#면책-조항)

## Model Context Protocol(MCP)이란 무엇이며, AWS용 MCP 서버와 어떻게 함께 동작하나요?

> Model Context Protocol(MCP)은 LLM 애플리케이션과 외부 데이터 소스 및 도구 간의 원활한 통합을 가능하게 하는 개방형 프로토콜입니다. AI 기반 IDE를 만들거나, 채팅 인터페이스를 개선하거나, 사용자 지정 AI 워크플로를 구축하는 경우에도 MCP는 LLM에 필요한 컨텍스트를 연결하는 표준화된 방법을 제공합니다.
>
> &mdash; [Model Context Protocol README](https://github.com/modelcontextprotocol#:~:text=The%20Model%20Context,context%20they%20need.)

MCP 서버는 표준화된 Model Context Protocol을 통해 특정 기능을 노출하는 경량 프로그램입니다. 호스트 애플리케이션(챗봇, IDE, 기타 AI 도구 등)에는 MCP 서버와 1:1 연결을 유지하는 MCP 클라이언트가 있습니다. 대표적인 MCP 클라이언트로는 에이전트형 AI 코딩 어시스턴트(Kiro, Cline, Cursor, Windsurf 등)와 Claude Desktop 같은 챗봇 애플리케이션이 있으며, 지원 클라이언트는 계속 늘어나고 있습니다. MCP 서버는 로컬 데이터 소스와 원격 서비스에 접근하여 모델의 출력 품질을 높이는 추가 컨텍스트를 제공할 수 있습니다.

AWS용 MCP 서버는 이 프로토콜을 사용하여 AI 애플리케이션이 AWS 문서, 맥락에 맞는 안내, 모범 사례에 접근할 수 있도록 합니다. 표준화된 MCP 클라이언트-서버 아키텍처를 통해 AWS의 기능이 개발 환경 또는 AI 애플리케이션의 지능적인 확장이 됩니다.

AWS용 MCP 서버는 향상된 클라우드 네이티브 개발, 인프라 관리, 개발 워크플로를 지원하여 AI 기반 클라우드 컴퓨팅을 더 쉽고 효율적으로 만들어 줍니다.

Model Context Protocol은 Anthropic, PBC.가 운영하는 오픈 소스 프로젝트로, 커뮤니티 전체의 기여에 열려 있습니다. MCP에 대한 자세한 내용은 [여기](https://modelcontextprotocol.io/introduction)에서 추가 문서를 확인할 수 있습니다.

## AWS용 오픈 소스 MCP 서버의 전송 메커니즘

### 지원되는 전송 메커니즘

MCP 프로토콜은 현재 클라이언트-서버 통신을 위한 두 가지 표준 전송 메커니즘을 정의합니다:
- stdio: 표준 입력과 표준 출력을 통한 통신
- streamable HTTP

이 리포지토리의 MCP 서버는 stdio만 지원하도록 설계되어 있습니다.

이러한 서버의 사용이 해당 서버에 적용되는 약관 및 사용자에게 적용되는 모든 법률, 규칙, 규정, 정책, 표준을 준수하도록 보장할 책임은 사용자에게 있습니다.

### Server Sent Events(SSE) 지원 중단

**중요 공지:** 2025년 5월 26일부터 모든 MCP 서버의 최신 메이저 버전에서 Server Sent Events(SSE) 지원이 제거되었습니다. 이 변경 사항은 Model Context Protocol 명세의 [하위 호환성 가이드라인](https://modelcontextprotocol.io/specification/2025-03-26/basic/transports#backwards-compatibility)을 따릅니다.

향후 버전에서 개선된 전송 기능을 제공할 [Streamable HTTP](https://modelcontextprotocol.io/specification/draft/basic/transports#streamable-http) 지원을 적극적으로 준비하고 있습니다.

여전히 SSE 지원이 필요한 애플리케이션은 대체 전송 방식으로 마이그레이션할 수 있을 때까지 해당 MCP 서버의 이전 메이저 버전을 사용하세요.

### AWS용 MCP 서버가 필요한 이유

MCP 서버는 다음과 같은 핵심적인 방식으로 파운데이션 모델(FM)의 역량을 강화합니다:

- **출력 품질 향상**: 관련 정보를 모델의 컨텍스트에 직접 제공함으로써 AWS 서비스와 같은 전문 영역에 대한 모델 응답을 크게 개선합니다. 이 방식은 환각(hallucination)을 줄이고, 더 정확한 기술 세부 정보를 제공하며, 보다 정밀한 코드 생성을 가능하게 하고, 권장 사항이 최신 AWS 모범 사례 및 서비스 기능에 부합하도록 보장합니다.

- **최신 문서 접근**: FM은 최근 출시된 기능, API, SDK를 알지 못할 수 있습니다. MCP 서버는 최신 문서를 가져와 이 격차를 메우고, AI 어시스턴트가 항상 최신 AWS 기능을 기준으로 동작하도록 합니다.

- **워크플로 자동화**: MCP 서버는 일반적인 워크플로를 파운데이션 모델이 직접 사용할 수 있는 도구로 변환합니다. CDK, Terraform 또는 기타 AWS 특화 워크플로에서 이러한 도구를 통해 AI 어시스턴트가 복잡한 작업을 더 정확하고 효율적으로 수행할 수 있습니다.

- **전문 도메인 지식**: MCP 서버는 파운데이션 모델의 학습 데이터에 충분히 반영되지 않았을 수 있는 AWS 서비스에 대한 깊이 있는 맥락적 지식을 제공하여, 클라우드 개발 작업에 대해 더 정확하고 유용한 응답을 가능하게 합니다.

## 사용 가능한 MCP 서버: 빠른 설치

주요 MCP 클라이언트용 원클릭 설치 버튼으로 빠르게 시작하세요. 아래 버튼을 클릭하면 Cursor 또는 VS Code에 서버를 바로 설치할 수 있습니다:

### 🚀 AWS 시작하기

AWS와 상호 작용할 때는 다음 서버부터 시작하는 것을 권장합니다:

| 서버 이름 | 설명 | 설치 |
|-------------------------------------------------------------------------------------------------------------|-------------|---------|
| [AWS MCP Server (in preview)](https://docs.aws.amazon.com/aws-mcp/latest/userguide/what-is-mcp-server.html) | 안전하고 감사 가능한 AWS 상호 작용은 여기서 시작하세요! AWS가 호스팅하는 원격 관리형 MCP 서버로, 포괄적인 AWS API 지원과 최신 AWS 문서, API 참조, What's New 게시물, 시작 안내 정보에 대한 접근을 함께 제공합니다. AWS 모범 사례를 따르는 사전 구축된 Agent SOP를 제공하여 에이전트가 복잡한 다단계 AWS 작업을 안정적으로 완료할 수 있도록 지원합니다. 안전성과 제어를 고려하여 설계되었습니다: 구문이 검증된 API 호출, 자격 증명 노출이 없는 IAM 기반 권한, 완전한 CloudTrail 감사 로깅. 모든 AWS 서비스에 접근하여 인프라를 관리하고 리소스를 탐색하며 완전한 투명성과 추적성을 갖춘 AWS 작업을 실행할 수 있습니다. [자세히 보기](https://docs.aws.amazon.com/aws-mcp/latest/userguide/what-is-mcp-server.html) | [![Install](https://img.shields.io/badge/Install-Kiro-9046FF?style=flat-square&logo=kiro)](https://kiro.dev/launch/mcp/add?name=aws-mcp&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22mcp-proxy-for-aws%40latest%22%2C%22https%3A//aws-mcp.us-east-1.api.aws/mcp%22%5D%7D) <br/>[![Install](https://img.shields.io/badge/Install-Cursor-blue?style=flat-square&logo=cursor)](https://cursor.com/en-US/install-mcp?name=aws-mcp&config=eyJjb21tYW5kIjoidXZ4IG1jcC1wcm94eS1mb3ItYXdzQGxhdGVzdCBodHRwczovL2F3cy1tY3AudXMtZWFzdC0xLmFwaS5hd3MvbWNwIn0%3D) <br/>[![Install on VS Code](https://img.shields.io/badge/Install-VS_Code-FF9900?style=flat-square&logo=visualstudiocode&logoColor=white)](<https://insiders.vscode.dev/redirect/mcp/install?name=AWS%20MCP%20Server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22mcp-proxy-for-aws%40latest%22%2C%22https%3A%2F%2Faws-mcp.us-east-1.api.aws%2Fmcp%22%5D%7D>) |

### 구축 대상별로 살펴보기

#### 📚 공식 AWS 문서에 대한 실시간 접근

| 서버 이름 | 설명 | 설치 |
|-------------|-------------|---------|
| [AWS Knowledge MCP Server](src/aws-knowledge-mcp-server) | AWS가 호스팅하는 원격 완전 관리형 MCP 서버로, 최신 AWS 문서, API 참조, What's New 게시물, 시작 안내 정보, Builder Center, 블로그 게시물, 아키텍처 참조, Well-Architected 가이드에 대한 접근을 제공합니다. | [![Install](https://img.shields.io/badge/Install-Kiro-9046FF?style=flat-square&logo=kiro)](https://kiro.dev/launch/mcp/add?name=aws-knowledge-mcp&config=%7B%22url%22%3A%22https%3A//knowledge-mcp.global.api.aws%22%7D) <br/>[![Install](https://img.shields.io/badge/Install-Cursor-blue?style=flat-square&logo=cursor)](https://cursor.com/en/install-mcp?name=aws-knowledge-mcp&config=eyJ1cmwiOiJodHRwczovL2tub3dsZWRnZS1tY3AuZ2xvYmFsLmFwaS5hd3MifQ==) <br/>[![Install on VS Code](https://img.shields.io/badge/Install-VS_Code-FF9900?style=flat-square&logo=visualstudiocode&logoColor=white)](https://vscode.dev/redirect/mcp/install?name=aws-knowledge-mcp&config=%7B%22type%22%3A%22http%22%2C%22url%22%3A%22https%3A%2F%2Fknowledge-mcp.global.api.aws%22%7D) |
| [AWS Documentation MCP Server](src/aws-documentation-mcp-server) | 최신 AWS 문서와 API 참조 조회 | [![Install](https://img.shields.io/badge/Install-Kiro-9046FF?style=flat-square&logo=kiro)](https://kiro.dev/launch/mcp/add?name=awslabs.aws-documentation-mcp-server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.aws-documentation-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%2C%22AWS_DOCUMENTATION_PARTITION%22%3A%22aws%22%7D%7D) <br/>[![Install](https://img.shields.io/badge/Install-Cursor-blue?style=flat-square&logo=cursor)](https://cursor.com/en/install-mcp?name=awslabs.aws-documentation-mcp-server&config=eyJjb21tYW5kIjoidXZ4IGF3c2xhYnMuYXdzLWRvY3VtZW50YXRpb24tbWNwLXNlcnZlckBsYXRlc3QiLCJlbnYiOnsiRkFTVE1DUF9MT0dfTEVWRUwiOiJFUlJPUiIsIkFXU19ET0NVTUVOVEFUSU9OX1BBUlRJVElPTiI6ImF3cyJ9LCJkaXNhYmxlZCI6ZmFsc2UsImF1dG9BcHByb3ZlIjpbXX0%3D) <br/>[![Install on VS Code](https://img.shields.io/badge/Install-VS_Code-FF9900?style=flat-square&logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/redirect/mcp/install?name=AWS%20Documentation%20MCP%20Server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.aws-documentation-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%2C%22AWS_DOCUMENTATION_PARTITION%22%3A%22aws%22%7D%2C%22disabled%22%3Afalse%2C%22autoApprove%22%3A%5B%5D%7D) |


### 🏗️ 인프라 및 배포

코드형 인프라(IaC) 모범 사례에 따라 클라우드 인프라를 구축, 배포, 관리합니다.

| 서버 이름 | 설명 | 설치 |
|-------------|-------------|---------|
| [AWS IaC MCP Server](src/aws-iac-mcp-server) | CloudFormation 문서 접근, CDK 모범 사례 안내, 컨스트럭트 예제, 보안 검증, 배포 트러블슈팅을 제공하는 완전한 코드형 인프라(IaC) 툴킷 | [![Install](https://img.shields.io/badge/Install-Kiro-9046FF?style=flat-square&logo=kiro)](https://kiro.dev/launch/mcp/add?name=awslabs.aws-iac-mcp-server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.aws-iac-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22AWS_PROFILE%22%3A%22your-aws-profile%22%2C%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%7D%7D) <br/>[![Install](https://img.shields.io/badge/Install-Cursor-blue?style=flat-square&logo=cursor)](https://cursor.com/en/install-mcp?name=awslabs.aws-iac-mcp-server&config=eyJjb21tYW5kIjoidXZ4IGF3c2xhYnMuYXdzLWlhYy1tY3Atc2VydmVyQGxhdGVzdCIsImVudiI6eyJBV1NfUFJPRklMRSI6InlvdXItYXdzLXByb2ZpbGUiLCJGQVNUTUNQX0xPR19MRVZFTCI6IkVSUk9SIn0sImRpc2FibGVkIjpmYWxzZSwiYXV0b0FwcHJvdmUiOltdfQ==IiwiZW52Ijp7IkFXU19QUk9GSUxFIjoieW91ci1hd3MtcHJvZmlsZSIsIkZBU1RNQ1BfTE9HX0xFVkVMIjoiRVJST1IifSwiZGlzYWJsZWQiOmZhbHNlLCJhdXRvQXBwcm92ZSI6W119) <br/>[![Install on VS Code](https://img.shields.io/badge/Install-VS_Code-FF9900?style=flat-square&logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/redirect/mcp/install?name=AWS%20IaC%20MCP%20Server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.aws-iac-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22AWS_PROFILE%22%3A%22your-aws-profile%22%2C%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%7D%2C%22disabled%22%3Afalse%2C%22autoApprove%22%3A%5B%5D%7D) |
| [AWS Cloud Control API MCP Server](src/ccapi-mcp-server) ⚠️ **DEPRECATED** | 보안 스캐닝과 모범 사례를 갖춘 AWS 리소스 직접 관리 ([AWS IaC MCP Server](src/aws-iac-mcp-server)를 대신 사용하세요) | [![Install](https://img.shields.io/badge/Install-Kiro-9046FF?style=flat-square&logo=kiro)](https://kiro.dev/launch/mcp/add?name=awslabs.ccapi-mcp-server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.ccapi-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22AWS_PROFILE%22%3A%22your-aws-profile%22%2C%22AWS_REGION%22%3A%22us-east-1%22%2C%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%7D%7D) <br/>[![Install](https://img.shields.io/badge/Install-Cursor-blue?style=flat-square&logo=cursor)](https://cursor.com/en/install-mcp?name=awslabs.ccapi-mcp-server&config=eyJjb21tYW5kIjoidXZ4IGF3c2xhYnMuY2NhcGktbWNwLXNlcnZlckBsYXRlc3QiLCJlbnYiOnsiQVdTX1BST0ZJTEUiOiJ5b3VyLWF3cy1wcm9maWxlIiwiQVdTX1JFR0lPTiI6InVzLWVhc3QtMSIsIkZBU1RNQ1BfTE9HX0xFVkVMIjoiRVJST1IifSwiZGlzYWJsZWQiOmZhbHNlLCJhdXRvQXBwcm92ZSI6W119) <br/>[![Install on VS Code](https://img.shields.io/badge/Install-VS_Code-FF9900?style=flat-square&logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/redirect/mcp/install?name=AWS%20Cloud%20Control%20API%20MCP%20Server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.ccapi-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22AWS_PROFILE%22%3A%22your-aws-profile%22%2C%22AWS_REGION%22%3A%22us-east-1%22%2C%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%7D%2C%22disabled%22%3Afalse%2C%22autoApprove%22%3A%5B%5D%7D) |

#### 컨테이너 플랫폼

| 서버 이름 | 설명 | 설치 |
|-------------|-------------|---------|
| [Amazon EKS MCP Server](src/eks-mcp-server) | Kubernetes 클러스터 관리 및 애플리케이션 배포 | [![Install](https://img.shields.io/badge/Install-Kiro-9046FF?style=flat-square&logo=kiro)](https://kiro.dev/launch/mcp/add?name=awslabs.eks-mcp-server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.eks-mcp-server%40latest%22%2C%22--allow-write%22%2C%22--allow-sensitive-data-access%22%5D%2C%22env%22%3A%7B%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%7D%7D) <br/>[![Install](https://img.shields.io/badge/Install-Cursor-blue?style=flat-square&logo=cursor)](https://cursor.com/en/install-mcp?name=awslabs.eks-mcp-server&config=eyJhdXRvQXBwcm92ZSI6W10sImRpc2FibGVkIjpmYWxzZSwiY29tbWFuZCI6InV2eCBhd3NsYWJzLmVrcy1tY3Atc2VydmVyQGxhdGVzdCAtLWFsbG93LXdyaXRlIC0tYWxsb3ctc2Vuc2l0aXZlLWRhdGEtYWNjZXNzIiwiZW52Ijp7IkZBU1RNQ1BfTE9HX0xFVkVMIjoiRVJST1IifSwidHJhbnNwb3J0VHlwZSI6InN0ZGlvIn0%3D) <br/>[![Install on VS Code](https://img.shields.io/badge/Install-VS_Code-FF9900?style=flat-square&logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/redirect/mcp/install?name=EKS%20MCP%20Server&config=%7B%22autoApprove%22%3A%5B%5D%2C%22disabled%22%3Afalse%2C%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.eks-mcp-server%40latest%22%2C%22--allow-write%22%2C%22--allow-sensitive-data-access%22%5D%2C%22env%22%3A%7B%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%7D%2C%22transportType%22%3A%22stdio%22%7D) |
| [Amazon ECS MCP Server](src/ecs-mcp-server) | 컨테이너 오케스트레이션 및 ECS 애플리케이션 배포 | [![Install](https://img.shields.io/badge/Install-Kiro-9046FF?style=flat-square&logo=kiro)](https://kiro.dev/launch/mcp/add?name=awslabs.ecs-mcp-server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22--from%22%2C%22awslabs-ecs-mcp-server%22%2C%22ecs-mcp-server%22%5D%2C%22env%22%3A%7B%22AWS_PROFILE%22%3A%22your-aws-profile%22%2C%22AWS_REGION%22%3A%22your-aws-region%22%2C%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%2C%22FASTMCP_LOG_FILE%22%3A%22/path/to/ecs-mcp-server.log%22%2C%22ALLOW_WRITE%22%3A%22false%22%2C%22ALLOW_SENSITIVE_DATA%22%3A%22false%22%7D%7D) <br/>[![Install](https://img.shields.io/badge/Install-Cursor-blue?style=flat-square&logo=cursor)](https://cursor.com/en/install-mcp?name=awslabs.ecs-mcp-server&config=eyJjb21tYW5kIjoidXZ4IC0tZnJvbSBhd3NsYWJzLWVjcy1tY3Atc2VydmVyIGVjcy1tY3Atc2VydmVyIiwiZW52Ijp7IkFXU19QUk9GSUxFIjoieW91ci1hd3MtcHJvZmlsZSIsIkFXU19SRUdJT04iOiJ5b3VyLWF3cy1yZWdpb24iLCJGQVNUTUNQX0xPR19MRVZFTCI6IkVSUk9SIiwiRkFTVE1DUF9MT0dfRklMRSI6Ii9wYXRoL3RvL2Vjcy1tY3Atc2VydmVyLmxvZyIsIkFMTE9XX1dSSVRFIjoiZmFsc2UiLCJBTExPV19TRU5TSVRJVkVfREFUQSI6ImZhbHNlIn19) <br/>[![Install on VS Code](https://img.shields.io/badge/Install-VS_Code-FF9900?style=flat-square&logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/redirect/mcp/install?name=ECS%20MCP%20Server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22--from%22%2C%22awslabs-ecs-mcp-server%22%2C%22ecs-mcp-server%22%5D%2C%22env%22%3A%7B%22AWS_PROFILE%22%3A%22your-aws-profile%22%2C%22AWS_REGION%22%3A%22your-aws-region%22%2C%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%2C%22FASTMCP_LOG_FILE%22%3A%22%2Fpath%2Fto%2Fecs-mcp-server.log%22%2C%22ALLOW_WRITE%22%3A%22false%22%2C%22ALLOW_SENSITIVE_DATA%22%3A%22false%22%7D%7D) |
| [Finch MCP Server](src/finch-mcp-server) | ECR 연동을 통한 로컬 컨테이너 빌드 | [![Install](https://img.shields.io/badge/Install-Kiro-9046FF?style=flat-square&logo=kiro)](https://kiro.dev/launch/mcp/add?name=awslabs.finch-mcp-server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.finch-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22AWS_PROFILE%22%3A%22default%22%2C%22AWS_REGION%22%3A%22us-west-2%22%2C%22FASTMCP_LOG_LEVEL%22%3A%22INFO%22%7D%7D) <br/>[![Install](https://img.shields.io/badge/Install-Cursor-blue?style=flat-square&logo=cursor)](https://cursor.com/en/install-mcp?name=awslabs.finch-mcp-server&config=eyJjb21tYW5kIjoidXZ4IGF3c2xhYnMuZmluY2gtbWNwLXNlcnZlckBsYXRlc3QiLCJlbnYiOnsiQVdTX1BST0ZJTEUiOiJkZWZhdWx0IiwiQVdTX1JFR0lPTiI6InVzLXdlc3QtMiIsIkZBU1RNQ1BfTE9HX0xFVkVMIjoiSU5GTyJ9LCJ0cmFuc3BvcnRUeXBlIjoic3RkaW8iLCJkaXNhYmxlZCI6ZmFsc2UsImF1dG9BcHByb3ZlIjpbXX0%3D) <br/>[![Install on VS Code](https://img.shields.io/badge/Install-VS_Code-FF9900?style=flat-square&logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/redirect/mcp/install?name=Finch%20MCP%20Server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.finch-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22AWS_PROFILE%22%3A%22default%22%2C%22AWS_REGION%22%3A%22us-west-2%22%2C%22FASTMCP_LOG_LEVEL%22%3A%22INFO%22%7D%2C%22transportType%22%3A%22stdio%22%2C%22disabled%22%3Afalse%2C%22autoApprove%22%3A%5B%5D%7D) |



#### 서버리스 및 함수

| 서버 이름 | 설명 | 설치 |
|-------------|-------------|---------|
| [AWS Serverless MCP Server](src/aws-serverless-mcp-server) | SAM CLI를 활용한 서버리스 애플리케이션 전체 수명 주기 관리 | [![Install](https://img.shields.io/badge/Install-Kiro-9046FF?style=flat-square&logo=kiro)](https://kiro.dev/launch/mcp/add?name=awslabs.aws-serverless-mcp-server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.aws-serverless-mcp-server%40latest%22%2C%22--allow-write%22%2C%22--allow-sensitive-data-access%22%5D%2C%22env%22%3A%7B%22AWS_PROFILE%22%3A%22your-aws-profile%22%2C%22AWS_REGION%22%3A%22us-east-1%22%7D%7D) <br/>[![Install](https://img.shields.io/badge/Install-Cursor-blue?style=flat-square&logo=cursor)](https://cursor.com/en/install-mcp?name=awslabs.aws-serverless-mcp-server&config=eyJjb21tYW5kIjoidXZ4IGF3c2xhYnMuYXdzLXNlcnZlcmxlc3MtbWNwLXNlcnZlckBsYXRlc3QgLS1hbGxvdy13cml0ZSAtLWFsbG93LXNlbnNpdGl2ZS1kYXRhLWFjY2VzcyIsImVudiI6eyJBV1NfUFJPRklMRSI6InlvdXItYXdzLXByb2ZpbGUiLCJBV1NfUkVHSU9OIjoidXMtZWFzdC0xIn0sImRpc2FibGVkIjpmYWxzZSwiYXV0b0FwcHJvdmUiOltdfQ%3D%3D) <br/>[![Install on VS Code](https://img.shields.io/badge/Install-VS_Code-FF9900?style=flat-square&logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/redirect/mcp/install?name=AWS%20Serverless%20MCP%20Server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.aws-serverless-mcp-server%40latest%22%2C%22--allow-write%22%2C%22--allow-sensitive-data-access%22%5D%2C%22env%22%3A%7B%22AWS_PROFILE%22%3A%22your-aws-profile%22%2C%22AWS_REGION%22%3A%22us-east-1%22%7D%2C%22disabled%22%3Afalse%2C%22autoApprove%22%3A%5B%5D%7D) |
| [AWS Lambda Tool MCP Server](src/lambda-tool-mcp-server) | 프라이빗 리소스 접근을 위해 Lambda 함수를 AI 도구로 실행 | [![Install](https://img.shields.io/badge/Install-Kiro-9046FF?style=flat-square&logo=kiro)](https://kiro.dev/launch/mcp/add?name=awslabs.lambda-tool-mcp-server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.lambda-tool-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22AWS_PROFILE%22%3A%22your-aws-profile%22%2C%22AWS_REGION%22%3A%22us-east-1%22%2C%22FUNCTION_PREFIX%22%3A%22your-function-prefix%22%2C%22FUNCTION_LIST%22%3A%22your-first-function%2C%20your-second-function%22%2C%22FUNCTION_TAG_KEY%22%3A%22your-tag-key%22%2C%22FUNCTION_TAG_VALUE%22%3A%22your-tag-value%22%2C%22FUNCTION_INPUT_SCHEMA_ARN_TAG_KEY%22%3A%22your-function-tag-for-input-schema%22%7D%7D) <br/>[![Install](https://img.shields.io/badge/Install-Cursor-blue?style=flat-square&logo=cursor)](https://cursor.com/en/install-mcp?name=awslabs.lambda-tool-mcp-server&config=eyJjb21tYW5kIjoidXZ4IGF3c2xhYnMubGFtYmRhLXRvb2wtbWNwLXNlcnZlckBsYXRlc3QiLCJlbnYiOnsiQVdTX1BST0ZJTEUiOiJ5b3VyLWF3cy1wcm9maWxlIiwiQVdTX1JFR0lPTiI6InVzLWVhc3QtMSIsIkZVTkNUSU9OX1BSRUZJWCI6InlvdXItZnVuY3Rpb24tcHJlZml4IiwiRlVOQ1RJT05fTElTVCI6InlvdXItZmlyc3QtZnVuY3Rpb24sIHlvdXItc2Vjb25kLWZ1bmN0aW9uIiwiRlVOQ1RJT05fVEFHX0tFWSI6InlvdXItdGFnLWtleSIsIkZVTkNUSU9OX1RBR19WQUxVRSI6InlvdXItdGFnLXZhbHVlIiwiRlVOQ1RJT05fSU5QVVRfU0NIRU1BX0FSTl9UQUdfS0VZIjoieW91ci1mdW5jdGlvbi10YWctZm9yLWlucHV0LXNjaGVtYSJ9fQ%3D%3D) <br/>[![Install on VS Code](https://img.shields.io/badge/Install-VS_Code-FF9900?style=flat-square&logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/redirect/mcp/install?name=AWS%20Lambda%20Tool%20MCP%20Server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.lambda-tool-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22AWS_PROFILE%22%3A%22your-aws-profile%22%2C%22AWS_REGION%22%3A%22us-east-1%22%2C%22FUNCTION_PREFIX%22%3A%22your-function-prefix%22%2C%22FUNCTION_LIST%22%3A%22your-first-function%2C%20your-second-function%22%2C%22FUNCTION_TAG_KEY%22%3A%22your-tag-key%22%2C%22FUNCTION_TAG_VALUE%22%3A%22your-tag-value%22%2C%22FUNCTION_INPUT_SCHEMA_ARN_TAG_KEY%22%3A%22your-function-tag-for-input-schema%22%7D%7D) |


#### 마이그레이션 및 현대화

| 서버 이름 | 설명 | 설치 |
|-------------|-------------|---------|
| [AWS Transform MCP Server](src/aws-transform-mcp-server) | 메인프레임, VMware, .NET 및 사용자 지정 코드 전환을 위한 AWS Transform 워크스페이스, 작업, 커넥터, HITL 태스크, 아티팩트 관리 | [![Install](https://img.shields.io/badge/Install-Kiro-9046FF?style=flat-square&logo=kiro)](https://kiro.dev/launch/mcp/add?name=awslabs.aws-transform-mcp-server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.aws-transform-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%7D%7D) <br/>[![Install](https://img.shields.io/badge/Install-Cursor-blue?style=flat-square&logo=cursor)](https://cursor.com/en/install-mcp?name=awslabs.aws-transform-mcp-server&config=eyJjb21tYW5kIjoidXZ4IGF3c2xhYnMuYXdzLXRyYW5zZm9ybS1tY3Atc2VydmVyQGxhdGVzdCIsImVudiI6eyJGQVNUTUNQX0xPR19MRVZFTCI6IkVSUk9SIn0sImRpc2FibGVkIjpmYWxzZSwiYXV0b0FwcHJvdmUiOltdfQ==) <br/>[![Install on VS Code](https://img.shields.io/badge/Install-VS_Code-FF9900?style=flat-square&logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/redirect/mcp/install?name=AWS%20Transform%20MCP%20Server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.aws-transform-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%7D%2C%22disabled%22%3Afalse%2C%22autoApprove%22%3A%5B%5D%7D) |

#### 지원

| 서버 이름 | 설명 | 설치 |
|-------------|-------------|---------|
| [AWS Support MCP Server](src/aws-support-mcp-server) | AWS Support 케이스 생성 및 관리 지원 | [![Install](https://img.shields.io/badge/Install-Kiro-9046FF?style=flat-square&logo=kiro)](https://kiro.dev/launch/mcp/add?name=awslabs_support_mcp_server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22-m%22%2C%22awslabs.aws-support-mcp-server%40latest%22%2C%22--debug%22%2C%22--log-file%22%2C%22./logs/mcp_support_server.log%22%5D%2C%22env%22%3A%7B%22AWS_PROFILE%22%3A%22your-aws-profile%22%7D%7D) <br/>[![Install](https://img.shields.io/badge/Install-Cursor-blue?style=flat-square&logo=cursor)](https://cursor.com/en/install-mcp?name=awslabs_support_mcp_server&config=eyJjb21tYW5kIjoidXZ4IC1tIGF3c2xhYnMuYXdzLXN1cHBvcnQtbWNwLXNlcnZlckBsYXRlc3QgLS1kZWJ1ZyAtLWxvZy1maWxlIC4vbG9ncy9tY3Bfc3VwcG9ydF9zZXJ2ZXIubG9nIiwiZW52Ijp7IkFXU19QUk9GSUxFIjoieW91ci1hd3MtcHJvZmlsZSJ9fQ%3D%3D) <br/>[![Install on VS Code](https://img.shields.io/badge/Install-VS_Code-FF9900?style=flat-square&logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/redirect/mcp/install?name=AWS%20Support%20MCP%20Server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22-m%22%2C%22awslabs.aws-support-mcp-server%40latest%22%2C%22--debug%22%2C%22--log-file%22%2C%22.%2Flogs%2Fmcp_support_server.log%22%5D%2C%22env%22%3A%7B%22AWS_PROFILE%22%3A%22your-aws-profile%22%7D%7D) |

### 🤖 AI 및 머신 러닝
지식 검색, 콘텐츠 생성, ML 기능으로 AI 애플리케이션을 강화합니다.

| 서버 이름 | 설명 | 설치 |
|-------------|-------------|---------|
| [Amazon Bedrock Knowledge Bases Retrieval MCP Server ](src/bedrock-kb-retrieval-mcp-server) | 인용 정보를 포함한 엔터프라이즈 기술 자료 조회 | [![Install](https://img.shields.io/badge/Install-Kiro-9046FF?style=flat-square&logo=kiro)](https://kiro.dev/launch/mcp/add?name=awslabs.bedrock-kb-retrieval-mcp-server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.bedrock-kb-retrieval-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22AWS_PROFILE%22%3A%22your-profile-name%22%2C%22AWS_REGION%22%3A%22us-east-1%22%2C%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%2C%22KB_INCLUSION_TAG_KEY%22%3A%22optional-tag-key-to-filter-kbs%22%2C%22BEDROCK_KB_RERANKING_ENABLED%22%3A%22false%22%7D%7D) <br/>[![Install](https://img.shields.io/badge/Install-Cursor-blue?style=flat-square&logo=cursor)](https://cursor.com/en/install-mcp?name=awslabs.bedrock-kb-retrieval-mcp-server&config=eyJjb21tYW5kIjoidXZ4IGF3c2xhYnMuYmVkcm9jay1rYi1yZXRyaWV2YWwtbWNwLXNlcnZlckBsYXRlc3QiLCJlbnYiOnsiQVdTX1BST0ZJTEUiOiJ5b3VyLXByb2ZpbGUtbmFtZSIsIkFXU19SRUdJT04iOiJ1cy1lYXN0LTEiLCJGQVNUTUNQX0xPR19MRVZFTCI6IkVSUk9SIiwiS0JfSU5DTFVTSU9OX1RBR19LRVkiOiJvcHRpb25hbC10YWcta2V5LXRvLWZpbHRlci1rYnMiLCJCRURST0NLX0tCX1JFUkFOS0lOR19FTkFCTEVEIjoiZmFsc2UifSwiZGlzYWJsZWQiOmZhbHNlLCJhdXRvQXBwcm92ZSI6W119) <br/>[![Install on VS Code](https://img.shields.io/badge/Install-VS_Code-FF9900?style=flat-square&logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/redirect/mcp/install?name=Bedrock%20KB%20Retrieval%20MCP%20Server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.bedrock-kb-retrieval-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22AWS_PROFILE%22%3A%22your-profile-name%22%2C%22AWS_REGION%22%3A%22us-east-1%22%2C%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%2C%22KB_INCLUSION_TAG_KEY%22%3A%22optional-tag-key-to-filter-kbs%22%2C%22BEDROCK_KB_RERANKING_ENABLED%22%3A%22false%22%7D%2C%22disabled%22%3Afalse%2C%22autoApprove%22%3A%5B%5D%7D) |
| [Amazon Kendra Index MCP Server](src/amazon-kendra-index-mcp-server) | 엔터프라이즈 검색 및 RAG 강화 | [![Install](https://img.shields.io/badge/Install-Kiro-9046FF?style=flat-square&logo=kiro)](https://kiro.dev/launch/mcp/add?name=awslabs.amazon-kendra-index-mcp-server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.amazon-kendra-index-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22AWS_REGION%22%3A%22us-east-1%22%2C%22KEND_INDEX_ID%22%3A%22your-kendra-index-id%22%2C%22KEND_ROLE_ARN%22%3A%22your-kendra-role-arn%22%2C%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%7D%7D) <br/>[![Install](https://img.shields.io/badge/Install-Cursor-blue?style=flat-square&logo=cursor)](https://cursor.com/en/install-mcp?name=awslabs.amazon-kendra-index-mcp-server&config=eyJjb21tYW5kIjoidXZ4IGF3c2xhYnMuYW1hem9uLWtlbmRyYS1pbmRleC1tY3Atc2VydmVyQGxhdGVzdCIsImVudiI6eyJBV1NfUkVHSU9OIjoidXMtZWFzdC0xIiwiS0VORF9JTkRFWF9JRCI6InlvdXIta2VuZHJhLWluZGV4LWlkIiwiS0VORF9ST0xFX0FSTiI6InlvdXIta2VuZHJhLXJvbGUtYXJuIiwiRkFTVE1DUF9MT0dfTEVWRUwiOiJFUlJPUiJ9LCJkaXNhYmxlZCI6ZmFsc2UsImF1dG9BcHByb3ZlIjpbXX0%3D) <br/>[![Install on VS Code](https://img.shields.io/badge/Install-VS_Code-FF9900?style=flat-square&logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/redirect/mcp/install?name=Amazon%20Kendra%20Index%20MCP%20Server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.amazon-kendra-index-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22AWS_REGION%22%3A%22us-east-1%22%2C%22KEND_INDEX_ID%22%3A%22your-kendra-index-id%22%2C%22KEND_ROLE_ARN%22%3A%22your-kendra-role-arn%22%2C%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%7D%2C%22disabled%22%3Afalse%2C%22autoApprove%22%3A%5B%5D%7D) |
| [Amazon Q Business MCP Server](src/amazon-qbusiness-anonymous-mcp-server) | 익명 접근을 지원하는, 수집된 콘텐츠 기반 AI 어시스턴트 | [![Install](https://img.shields.io/badge/Install-Kiro-9046FF?style=flat-square&logo=kiro)](https://kiro.dev/launch/mcp/add?name=awslabs.amazon-qbusiness-anonymous-mcp-server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.amazon-qbusiness-anonymous-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22QBUSINESS_APP_ID%22%3A%22your-qbusiness-app-id%22%2C%22QBUSINESS_USER_ID%22%3A%22your-user-id%22%2C%22AWS_PROFILE%22%3A%22your-aws-profile%22%2C%22AWS_REGION%22%3A%22us-east-1%22%2C%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%7D%7D) <br/>[![Install](https://img.shields.io/badge/Install-Cursor-blue?style=flat-square&logo=cursor)](https://cursor.com/en/install-mcp?name=awslabs.amazon-qbusiness-anonymous-mcp-server&config=eyJjb21tYW5kIjoidXZ4IGF3c2xhYnMuYW1hem9uLXFidXNpbmVzcy1hbm9ueW1vdXMtbWNwLXNlcnZlckBsYXRlc3QiLCJlbnYiOnsiUUJVU0lORVNTX0FQUF9JRCI6InlvdXItcWJ1c2luZXNzLWFwcC1pZCIsIlFCVVNJTkVTU19VU0VSX0lEIjoieW91ci11c2VyLWlkIiwiQVdTX1BST0ZJTEUiOiJ5b3VyLWF3cy1wcm9maWxlIiwiQVdTX1JFR0lPTiI6InVzLWVhc3QtMSIsIkZBU1RNQ1BfTE9HX0xFVkVMIjoiRVJST1IifSwiZGlzYWJsZWQiOmZhbHNlLCJhdXRvQXBwcm92ZSI6W119) <br/>[![Install on VS Code](https://img.shields.io/badge/Install-VS_Code-FF9900?style=flat-square&logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/redirect/mcp/install?name=Amazon%20Q%20Business%20Anonymous%20MCP%20Server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.amazon-qbusiness-anonymous-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22QBUSINESS_APP_ID%22%3A%22your-qbusiness-app-id%22%2C%22QBUSINESS_USER_ID%22%3A%22your-user-id%22%2C%22AWS_PROFILE%22%3A%22your-aws-profile%22%2C%22AWS_REGION%22%3A%22us-east-1%22%2C%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%7D%2C%22disabled%22%3Afalse%2C%22autoApprove%22%3A%5B%5D%7D) |
| [Amazon Q Index MCP Server](src/amazon-qindex-mcp-server) | 엔터프라이즈 Q 인덱스를 검색하는 데이터 액세서 | [![Install](https://img.shields.io/badge/Install-Kiro-9046FF?style=flat-square&logo=kiro)](https://kiro.dev/launch/mcp/add?name=awslabs.amazon-qindex-mcp-server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.amazon-qindex-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22AWS_REGION%22%3A%22us-east-1%22%2C%22QINDEX_ID%22%3A%22your-qindex-id%22%2C%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%7D%7D) <br/>[![Install](https://img.shields.io/badge/Install-Cursor-blue?style=flat-square&logo=cursor)](https://cursor.com/en/install-mcp?name=awslabs.amazon-qindex-mcp-server&config=eyJjb21tYW5kIjoidXZ4IGF3c2xhYnMuYW1hem9uLXFpbmRleC1tY3Atc2VydmVyQGxhdGVzdCIsImVudiI6eyJBV1NfUkVHSU9OIjoidXMtZWFzdC0xIiwiUUlOREVYX0lEIjoieW91ci1xaW5kZXgtaWQiLCJGQVNUTUNQX0xPR19MRVZFTCI6IkVSUk9SIn0sImRpc2FibGVkIjpmYWxzZSwiYXV0b0FwcHJvdmUiOltdfQ%3D%3D) <br/>[![Install on VS Code](https://img.shields.io/badge/Install-VS_Code-FF9900?style=flat-square&logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/redirect/mcp/install?name=Amazon%20Q%20Index%20MCP%20Server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.amazon-qindex-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22AWS_REGION%22%3A%22us-east-1%22%2C%22QINDEX_ID%22%3A%22your-qindex-id%22%2C%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%7D%2C%22disabled%22%3Afalse%2C%22autoApprove%22%3A%5B%5D%7D) |
| [AWS Bedrock Custom Model Import MCP Server](src/aws-bedrock-custom-model-import-mcp-server) | 온디맨드 추론을 위한 Bedrock 커스텀 모델 관리 | [![Install](https://img.shields.io/badge/Install-Kiro-9046FF?style=flat-square&logo=kiro)](https://kiro.dev/launch/mcp/add?name=aws-bedrock-custom-model-import-mcp-server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.aws-bedrock-custom-model-import-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22AWS_PROFILE%22%3A%22your-aws-profile%22%2C%22AWS_REGION%22%3A%22us-east-1%22%2C%22BEDROCK_MODEL_IMPORT_S3_BUCKET%22%3A%22your-s3-bucket-name%22%2C%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%7D%7D) <br/>[![Install](https://img.shields.io/badge/Install-Cursor-blue?style=flat-square&logo=cursor)](https://cursor.com/en/install-mcp?name=aws-bedrock-custom-model-import-mcp-server&config=eyJjb21tYW5kIjoidXZ4IGF3c2xhYnMuYXdzLWJlZHJvY2stY3VzdG9tLW1vZGVsLWltcG9ydC1tY3Atc2VydmVyQGxhdGVzdCIsImVudiI6eyJBV1NfUFJPRklMRSI6InlvdXItYXdzLXByb2ZpbGUiLCJBV1NfUkVHSU9OIjoidXMtZWFzdC0xIiwiQkVEUk9DS19NT0RFTF9JTVBPUlRfUzNfQlVDS0VUIjoieW91ci1zMy1idWNrZXQtbmFtZSIsIkZBU1RNQ1BfTE9HX0xFVkVMIjoiRVJST1IifSwiZGlzYWJsZWQiOmZhbHNlLCJhdXRvQXBwcm92ZSI6W119) <br/>[![Install on VS Code](https://img.shields.io/badge/Install-VS_Code-FF9900?style=flat-square&logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/redirect/mcp/install?name=AWS%20Bedrock%20Custom%20Model%20Import%20MCP%20Server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.aws-bedrock-custom-model-import-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22AWS_PROFILE%22%3A%22your-aws-profile%22%2C%22AWS_REGION%22%3A%22us-east-1%22%2C%22BEDROCK_MODEL_IMPORT_S3_BUCKET%22%3A%22your-s3-bucket-name%22%2C%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%7D%2C%22disabled%22%3Afalse%2C%22autoApprove%22%3A%5B%5D%7D) |
| [AWS Bedrock AgentCore MCP Server](src/amazon-bedrock-agentcore-mcp-server) | AgentCore 플랫폼 서비스, API, 모범 사례에 대한 포괄적인 문서 접근 제공 | [![Install](https://img.shields.io/badge/Install-Kiro-9046FF?style=flat-square&logo=kiro)](https://kiro.dev/launch/mcp/add?name=awslabs.amazon-bedrock-agentcore-mcp-server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.amazon-bedrock-agentcore-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%7D%7D) <br/>[![Install](https://img.shields.io/badge/Install-Cursor-blue?style=flat-square&logo=cursor)](https://cursor.com/en/install-mcp?name=awslabs.amazon-bedrock-agentcore-mcp-server&config=eyJjb21tYW5kIjoidXZ4IGF3c2xhYnMuYW1hem9uLWJlZHJvY2stYWdlbnRjb3JlLW1jcC1zZXJ2ZXJAbGF0ZXN0IiwiZW52Ijp7IkZBU1RNQ1BfTE9HX0xFVkVMIjoiRVJST1IifSwiZGlzYWJsZWQiOmZhbHNlLCJhdXRvQXBwcm92ZSI6W119) <br/>[![Install on VS Code](https://img.shields.io/badge/Install-VS_Code-FF9900?style=flat-square&logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/redirect/mcp/install?name=AWS%20Bedrock%20AgentCore%20MCP%20Server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.amazon-bedrock-agentcore-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%7D%2C%22disabled%22%3Afalse%2C%22autoApprove%22%3A%5B%5D%7D) |
| [Amazon Translate MCP Server](src/amazon-translate-mcp-server) | 배치 처리와 사용자 지정 용어집을 지원하는 75개 이상 언어의 신경망 기계 번역 | [![Install](https://img.shields.io/badge/Install-Kiro-9046FF?style=flat-square&logo=kiro)](https://kiro.dev/launch/mcp/add?name=awslabs.amazon-translate-mcp-server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.amazon-translate-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22AWS_PROFILE%22%3A%22your-aws-profile%22%2C%22AWS_REGION%22%3A%22us-east-1%22%2C%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%7D%7D) <br/>[![Install](https://img.shields.io/badge/Install-Cursor-blue?style=flat-square&logo=cursor)](https://cursor.com/en/install-mcp?name=awslabs.amazon-translate-mcp-server&config=eyJjb21tYW5kIjoidXZ4IGF3c2xhYnMuYW1hem9uLXRyYW5zbGF0ZS1tY3Atc2VydmVyQGxhdGVzdCIsImVudiI6eyJBV1NfUFJPRklMRSI6InlvdXItYXdzLXByb2ZpbGUiLCJBV1NfUkVHSU9OIjoidXMtZWFzdC0xIiwiRkFTVE1DUF9MT0dfTEVWRUwiOiJFUlJPUiJ9LCJkaXNhYmxlZCI6ZmFsc2UsImF1dG9BcHByb3ZlIjpbXX0%3D) <br/>[![Install on VS Code](https://img.shields.io/badge/Install-VS_Code-FF9900?style=flat-square&logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/redirect/mcp/install?name=Amazon%20Translate%20MCP%20Server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.amazon-translate-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22AWS_PROFILE%22%3A%22your-aws-profile%22%2C%22AWS_REGION%22%3A%22us-east-1%22%2C%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%7D%2C%22disabled%22%3Afalse%2C%22autoApprove%22%3A%5B%5D%7D) |
| [Amazon SageMaker AI MCP Server](src/sagemaker-ai-mcp-server) | SageMaker AI 리소스 관리 및 모델 개발 | [![Install](https://img.shields.io/badge/Install-Kiro-9046FF?style=flat-square&logo=kiro)](https://kiro.dev/launch/mcp/add?name=awslabs.sagemaker-ai-mcp-server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.sagemaker-ai-mcp-server%40latest%22%2C%22--allow-write%22%2C%22--allow-sensitive-data-access%22%5D%2C%22env%22%3A%7B%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%7D%7D) <br/>[![Install](https://img.shields.io/badge/Install-Cursor-blue?style=flat-square&logo=cursor)](https://cursor.com/en/install-mcp?name=awslabs.sagemaker-ai-mcp-server&config=eyJhdXRvQXBwcm92ZSI6W10sImRpc2FibGVkIjpmYWxzZSwiY29tbWFuZCI6InV2eCBhd3NsYWJzLnNhZ2VtYWtlci1haS1tY3Atc2VydmVyQGxhdGVzdCAtLWFsbG93LXdyaXRlIC0tYWxsb3ctc2Vuc2l0aXZlLWRhdGEtYWNjZXNzIiwiZW52Ijp7IkZBU1RNQ1BfTE9HX0xFVkVMIjoiRVJST1IifSwidHJhbnNwb3J0VHlwZSI6InN0ZGlvIn0%3D) <br/>[![Install on VS Code](https://img.shields.io/badge/Install-VS_Code-FF9900?style=flat-square&logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/redirect/mcp/install?name=SageMaker%20AI%20MCP%20Server&config=%7B%22autoApprove%22%3A%5B%5D%2C%22disabled%22%3Afalse%2C%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.sagemaker-ai-mcp-server%40latest%22%2C%22--allow-write%22%2C%22--allow-sensitive-data-access%22%5D%2C%22env%22%3A%7B%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%7D%2C%22transportType%22%3A%22stdio%22%7D) |
| [Registry of Open Data (RODA) MCP Server](src/roda-mcp-server) | AWS의 오픈 데이터셋 검색, 탐색, 미리 보기 | [![Install](https://img.shields.io/badge/Install-Kiro-9046FF?style=flat-square&logo=kiro)](https://kiro.dev/launch/mcp/add?name=awslabs.roda-mcp-server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.roda-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%7D%7D) <br/>[![Install](https://img.shields.io/badge/Install-Cursor-blue?style=flat-square&logo=cursor)](https://cursor.com/en/install-mcp?name=awslabs.roda-mcp-server&config=eyJjb21tYW5kIjoidXZ4IGF3c2xhYnMucm9kYS1tY3Atc2VydmVyQGxhdGVzdCIsImVudiI6eyJGQVNUTUNQX0xPR19MRVZFTCI6IkVSUk9SIn0sImRpc2FibGVkIjpmYWxzZSwiYXV0b0FwcHJvdmUiOltdfQ==) <br/>[![Install on VS Code](https://img.shields.io/badge/Install-VS_Code-FF9900?style=flat-square&logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/redirect/mcp/install?name=RODA%20MCP%20Server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.roda-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%7D%2C%22disabled%22%3Afalse%2C%22autoApprove%22%3A%5B%5D%7D) |


### 📊 데이터 및 분석

데이터베이스, 캐싱 시스템, 데이터 처리 워크플로를 다룹니다.

#### SQL 및 NoSQL 데이터베이스

| 서버 이름 | 설명 | 설치 |
|-------------|-------------|---------|
| [Amazon DynamoDB MCP Server](src/dynamodb-mcp-server) | DynamoDB 전문가 수준의 설계 가이드 및 데이터 모델링 지원 | [![Install](https://img.shields.io/badge/Install-Kiro-9046FF?style=flat-square&logo=kiro)](https://kiro.dev/launch/mcp/add?name=awslabs-dynamodb-mcp-server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.dynamodb-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22DDB-MCP-READONLY%22%3A%22true%22%2C%22AWS_PROFILE%22%3A%22default%22%2C%22AWS_REGION%22%3A%22us-west-2%22%2C%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%7D%7D) <br/>[![Install](https://img.shields.io/badge/Install-Cursor-blue?style=flat-square&logo=cursor)](https://cursor.com/en/install-mcp?name=awslabs-dynamodb-mcp-server&config=eyJjb21tYW5kIjoidXZ4IGF3c2xhYnMuZHluYW1vZGItbWNwLXNlcnZlckBsYXRlc3QiLCJlbnYiOnsiRERCLU1DUC1SRUFET05MWSI6InRydWUiLCJBV1NfUFJPRklMRSI6ImRlZmF1bHQiLCJBV1NfUkVHSU9OIjoidXMtd2VzdC0yIiwiRkFTVE1DUF9MT0dfTEVWRUwiOiJFUlJPUiJ9LCJkaXNhYmxlZCI6ZmFsc2UsImF1dG9BcHByb3ZlIjpbXX0%3D) <br/>[![Install on VS Code](https://img.shields.io/badge/Install-VS_Code-FF9900?style=flat-square&logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/redirect/mcp/install?name=DynamoDB%20MCP%20Server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.dynamodb-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22DDB-MCP-READONLY%22%3A%22true%22%2C%22AWS_PROFILE%22%3A%22default%22%2C%22AWS_REGION%22%3A%22us-west-2%22%2C%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%7D%2C%22disabled%22%3Afalse%2C%22autoApprove%22%3A%5B%5D%7D) |
| [Amazon Aurora PostgreSQL MCP Server](src/postgres-mcp-server) | RDS Data API를 통한 PostgreSQL 데이터베이스 작업 | [![Install](https://img.shields.io/badge/Install-Kiro-9046FF?style=flat-square&logo=kiro)](https://kiro.dev/launch/mcp/add?name=awslabs.postgres-mcp-server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.postgres-mcp-server%40latest%22%2C%22--connection-string%22%2C%22postgresql%3A//%5Busername%5D%3A%5Bpassword%5D%40%5Bhost%5D%3A%5Bport%5D/%5Bdatabase%5D%22%5D%2C%22env%22%3A%7B%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%7D%7D) <br/>[![Install](https://img.shields.io/badge/Install-Cursor-blue?style=flat-square&logo=cursor)](https://cursor.com/en/install-mcp?name=awslabs.postgres-mcp-server&config=eyJjb21tYW5kIjoidXZ4IGF3c2xhYnMucG9zdGdyZXMtbWNwLXNlcnZlckBsYXRlc3QgLS1jb25uZWN0aW9uLXN0cmluZyBwb3N0Z3Jlc3FsOi8vW3VzZXJuYW1lXTpbcGFzc3dvcmRdQFtob3N0XTpbcG9ydF0vW2RhdGFiYXNlXSIsImVudiI6eyJGQVNUTUNQX0xPR19MRVZFTCI6IkVSUk9SIn0sImRpc2FibGVkIjpmYWxzZSwiYXV0b0FwcHJvdmUiOltdLCJ0cmFuc3BvcnRUeXBlIjoic3RkaW8iLCJhdXRvU3RhcnQiOnRydWV9) <br/>[![Install on VS Code](https://img.shields.io/badge/Install-VS_Code-FF9900?style=flat-square&logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/redirect/mcp/install?name=PostgreSQL%20MCP%20Server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.postgres-mcp-server%40latest%22%2C%22--connection-string%22%2C%22postgresql%3A%2F%2F%5Busername%5D%3A%5Bpassword%5D%40%5Bhost%5D%3A%5Bport%5D%2F%5Bdatabase%5D%22%5D%2C%22env%22%3A%7B%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%7D%2C%22disabled%22%3Afalse%2C%22autoApprove%22%3A%5B%5D%2C%22transportType%22%3A%22stdio%22%2C%22autoStart%22%3Atrue%7D) |
| [Amazon Aurora MySQL MCP Server](src/mysql-mcp-server) | RDS Data API를 통한 MySQL 데이터베이스 작업 | [![Install](https://img.shields.io/badge/Install-Kiro-9046FF?style=flat-square&logo=kiro)](https://kiro.dev/launch/mcp/add?name=awslabs.mysql-mcp-server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.mysql-mcp-server%40latest%22%2C%22--resource_arn%22%2C%22%5Byour%22%2C%22data%5D%22%2C%22--secret_arn%22%2C%22%5Byour%22%2C%22data%5D%22%2C%22--database%22%2C%22%5Byour%22%2C%22data%5D%22%2C%22--region%22%2C%22%5Byour%22%2C%22data%5D%22%2C%22--readonly%22%2C%22True%22%5D%2C%22env%22%3A%7B%22AWS_PROFILE%22%3A%22your-aws-profile%22%2C%22AWS_REGION%22%3A%22us-east-1%22%2C%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%7D%7D) <br/>[![Install](https://img.shields.io/badge/Install-Cursor-blue?style=flat-square&logo=cursor)](https://cursor.com/en/install-mcp?name=awslabs.mysql-mcp-server&config=eyJjb21tYW5kIjoidXZ4IGF3c2xhYnMubXlzcWwtbWNwLXNlcnZlckBsYXRlc3QgLS1yZXNvdXJjZV9hcm4gW3lvdXIgZGF0YV0gLS1zZWNyZXRfYXJuIFt5b3VyIGRhdGFdIC0tZGF0YWJhc2UgW3lvdXIgZGF0YV0gLS1yZWdpb24gW3lvdXIgZGF0YV0gLS1yZWFkb25seSBUcnVlIiwiZW52Ijp7IkFXU19QUk9GSUxFIjoieW91ci1hd3MtcHJvZmlsZSIsIkFXU19SRUdJT04iOiJ1cy1lYXN0LTEiLCJGQVNUTUNQX0xPR19MRVZFTCI6IkVSUk9SIn0sImRpc2FibGVkIjpmYWxzZSwiYXV0b0FwcHJvdmUiOltdfQ%3D%3D) <br/>[![Install on VS Code](https://img.shields.io/badge/Install-VS_Code-FF9900?style=flat-square&logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/redirect/mcp/install?name=MySQL%20MCP%20Server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.mysql-mcp-server%40latest%22%2C%22--resource_arn%22%2C%22%5Byour%20data%5D%22%2C%22--secret_arn%22%2C%22%5Byour%20data%5D%22%2C%22--database%22%2C%22%5Byour%20data%5D%22%2C%22--region%22%2C%22%5Byour%20data%5D%22%2C%22--readonly%22%2C%22True%22%5D%2C%22env%22%3A%7B%22AWS_PROFILE%22%3A%22your-aws-profile%22%2C%22AWS_REGION%22%3A%22us-east-1%22%2C%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%7D%2C%22disabled%22%3Afalse%2C%22autoApprove%22%3A%5B%5D%7D) |
| [Amazon Aurora DSQL MCP Server](src/aurora-dsql-mcp-server) | PostgreSQL 호환 분산 SQL | [![Install](https://img.shields.io/badge/Install-Kiro-9046FF?style=flat-square&logo=kiro)](https://kiro.dev/launch/mcp/add?name=awslabs.aurora-dsql-mcp-server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.aurora-dsql-mcp-server%40latest%22%2C%22--cluster_endpoint%22%2C%22%5Byour%22%2C%22dsql%22%2C%22cluster%22%2C%22endpoint%5D%22%2C%22--region%22%2C%22%5Byour%22%2C%22dsql%22%2C%22cluster%22%2C%22region%2C%22%2C%22e.g.%22%2C%22us-east-1%5D%22%2C%22--database_user%22%2C%22%5Byour%22%2C%22dsql%22%2C%22username%5D%22%2C%22--profile%22%2C%22default%22%5D%2C%22env%22%3A%7B%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%7D%7D) <br/>[![Install](https://img.shields.io/badge/Install-Cursor-blue?style=flat-square&logo=cursor)](https://cursor.com/en/install-mcp?name=awslabs.aurora-dsql-mcp-server&config=eyJjb21tYW5kIjoidXZ4IGF3c2xhYnMuYXVyb3JhLWRzcWwtbWNwLXNlcnZlckBsYXRlc3QgLS1jbHVzdGVyX2VuZHBvaW50IFt5b3VyIGRzcWwgY2x1c3RlciBlbmRwb2ludF0gLS1yZWdpb24gW3lvdXIgZHNxbCBjbHVzdGVyIHJlZ2lvbiwgZS5nLiB1cy1lYXN0LTFdIC0tZGF0YWJhc2VfdXNlciBbeW91ciBkc3FsIHVzZXJuYW1lXSAtLXByb2ZpbGUgZGVmYXVsdCIsImVudiI6eyJGQVNUTUNQX0xPR19MRVZFTCI6IkVSUk9SIn0sImRpc2FibGVkIjpmYWxzZSwiYXV0b0FwcHJvdmUiOltdfQ%3D%3D) <br/>[![Install on VS Code](https://img.shields.io/badge/Install-VS_Code-FF9900?style=flat-square&logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/redirect/mcp/install?name=Aurora%20DSQL%20MCP%20Server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.aurora-dsql-mcp-server%40latest%22%2C%22--cluster_endpoint%22%2C%22%5Byour%20dsql%20cluster%20endpoint%5D%22%2C%22--region%22%2C%22%5Byour%20dsql%20cluster%20region%2C%20e.g.%20us-east-1%5D%22%2C%22--database_user%22%2C%22%5Byour%20dsql%20username%5D%22%2C%22--profile%22%2C%22default%22%5D%2C%22env%22%3A%7B%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%7D%2C%22disabled%22%3Afalse%2C%22autoApprove%22%3A%5B%5D%7D) |
| [Amazon DocumentDB MCP Server](src/documentdb-mcp-server) | MongoDB 호환 문서 데이터베이스 작업 | [![Install](https://img.shields.io/badge/Install-Kiro-9046FF?style=flat-square&logo=kiro)](https://kiro.dev/launch/mcp/add?name=awslabs.documentdb-mcp-server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.documentdb-mcp-serve%40latest%22%5D%2C%22env%22%3A%7B%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%2C%22AWS_PROFILE%22%3A%22your-aws-profile%22%7D%7D) <br/>[![Install](https://img.shields.io/badge/Install-Cursor-blue?style=flat-square&logo=cursor)](https://cursor.com/en/install-mcp?name=awslabs.documentdb-mcp-server&config=eyJjb21tYW5kIjoidXZ4IGF3c2xhYnMuZG9jdW1lbnRkYi1tY3Atc2VydmVAbGF0ZXN0IiwiZW52Ijp7IkZBU1RNQ1BfTE9HX0xFVkVMIjoiRVJST1IiLCJBV1NfUFJPRklMRSI6InlvdXItYXdzLXByb2ZpbGUifSwiZGlzYWJsZWQiOmZhbHNlLCJhdXRvQXBwcm92ZSI6W119) <br/>[![Install on VS Code](https://img.shields.io/badge/Install-VS_Code-FF9900?style=flat-square&logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/redirect/mcp/install?name=DocumentDB%20MCP%20Server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.documentdb-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%2C%22AWS_PROFILE%22%3A%22your-aws-profile%22%7D%2C%22disabled%22%3Afalse%2C%22autoApprove%22%3A%5B%5D%7D) |
| [Amazon Neptune MCP Server](src/amazon-neptune-mcp-server) | openCypher 및 Gremlin을 사용한 그래프 데이터베이스 쿼리 | [![Install](https://img.shields.io/badge/Install-Kiro-9046FF?style=flat-square&logo=kiro)](https://kiro.dev/launch/mcp/add?name=awslabs.amazon-neptune-mcp-server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.amazon-neptune-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22NEPTUNE_ENDPOINT%22%3A%22https%3A//your-neptune-cluster-id.region.neptune.amazonaws.com%3A8182%22%2C%22AWS_PROFILE%22%3A%22your-aws-profile%22%2C%22AWS_REGION%22%3A%22us-east-1%22%2C%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%7D%7D) <br/>[![Install](https://img.shields.io/badge/Install-Cursor-blue?style=flat-square&logo=cursor)](https://cursor.com/en/install-mcp?name=awslabs.amazon-neptune-mcp-server&config=eyJjb21tYW5kIjoidXZ4IGF3c2xhYnMuYW1hem9uLW5lcHR1bmUtbWNwLXNlcnZlckBsYXRlc3QiLCJlbnYiOnsiTkVQVFVORV9FTkRQT0lOVCI6Imh0dHBzOi8veW91ci1uZXB0dW5lLWNsdXN0ZXItaWQucmVnaW9uLm5lcHR1bmUuYW1hem9uYXdzLmNvbTo4MTgyIiwiQVdTX1BST0ZJTEUiOiJ5b3VyLWF3cy1wcm9maWxlIiwiQVdTX1JFR0lPTiI6InVzLWVhc3QtMSIsIkZBU1RNQ1BfTE9HX0xFVkVMIjoiRVJST1IifSwiZGlzYWJsZWQiOmZhbHNlLCJhdXRvQXBwcm92ZSI6W119) <br/>[![Install on VS Code](https://img.shields.io/badge/Install-VS_Code-FF9900?style=flat-square&logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/redirect/mcp/install?name=Amazon%20Neptune%20MCP%20Server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.amazon-neptune-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22NEPTUNE_ENDPOINT%22%3A%22https%3A%2F%2Fyour-neptune-cluster-id.region.neptune.amazonaws.com%3A8182%22%2C%22AWS_PROFILE%22%3A%22your-aws-profile%22%2C%22AWS_REGION%22%3A%22us-east-1%22%2C%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%7D%2C%22disabled%22%3Afalse%2C%22autoApprove%22%3A%5B%5D%7D) |
| [Amazon Keyspaces MCP Server](src/amazon-keyspaces-mcp-server) | Apache Cassandra 호환 작업 | [![Install](https://img.shields.io/badge/Install-Kiro-9046FF?style=flat-square&logo=kiro)](https://kiro.dev/launch/mcp/add?name=awslabs.amazon-keyspaces-mcp-server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.amazon-keyspaces-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22AWS_PROFILE%22%3A%22your-aws-profile%22%2C%22AWS_REGION%22%3A%22us-east-1%22%2C%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%7D%7D) <br/>[![Install](https://img.shields.io/badge/Install-Cursor-blue?style=flat-square&logo=cursor)](https://cursor.com/en/install-mcp?name=awslabs.amazon-keyspaces-mcp-server&config=eyJjb21tYW5kIjoidXZ4IGF3c2xhYnMuYW1hem9uLWtleXNwYWNlcy1tY3Atc2VydmVyQGxhdGVzdCIsImVudiI6eyJBV1NfUFJPRklMRSI6InlvdXItYXdzLXByb2ZpbGUiLCJBV1NfUkVHSU9OIjoidXMtZWFzdC0xIiwiRkFTVE1DUF9MT0dfTEVWRUwiOiJFUlJPUiJ9LCJkaXNhYmxlZCI6ZmFsc2UsImF1dG9BcHByb3ZlIjpbXX0%3D) <br/>[![Install on VS Code](https://img.shields.io/badge/Install-VS_Code-FF9900?style=flat-square&logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/redirect/mcp/install?name=Amazon%20Keyspaces%20MCP%20Server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.amazon-keyspaces-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22AWS_PROFILE%22%3A%22your-aws-profile%22%2C%22AWS_REGION%22%3A%22us-east-1%22%2C%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%7D%2C%22disabled%22%3Afalse%2C%22autoApprove%22%3A%5B%5D%7D) |
| [Amazon Timestream for InfluxDB MCP Server](src/timestream-for-influxdb-mcp-server) | 시계열 데이터베이스 작업 및 InfluxDB 호환성 | [![Install](https://img.shields.io/badge/Install-Kiro-9046FF?style=flat-square&logo=kiro)](https://kiro.dev/launch/mcp/add?name=awslabs.timestream-for-influxdb-mcp-server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.timestream-for-influxdb-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22AWS_PROFILE%22%3A%22your-aws-profile%22%2C%22AWS_REGION%22%3A%22us-east-1%22%2C%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%7D%7D) <br/>[![Install](https://img.shields.io/badge/Install-Cursor-blue?style=flat-square&logo=cursor)](https://cursor.com/en/install-mcp?name=awslabs.timestream-for-influxdb-mcp-server&config=eyJjb21tYW5kIjoidXZ4IGF3c2xhYnMudGltZXN0cmVhbS1mb3ItaW5mbHV4ZGItbWNwLXNlcnZlckBsYXRlc3QiLCJlbnYiOnsiQVdTX1BST0ZJTEUiOiJ5b3VyLWF3cy1wcm9maWxlIiwiQVdTX1JFR0lPTiI6InVzLWVhc3QtMSIsIkZBU1RNQ1BfTE9HX0xFVkVMIjoiRVJST1IifSwiZGlzYWJsZWQiOmZhbHNlLCJhdXRvQXBwcm92ZSI6W119) <br/>[![Install on VS Code](https://img.shields.io/badge/Install-VS_Code-FF9900?style=flat-square&logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/redirect/mcp/install?name=Timestream%20for%20InfluxDB%20MCP%20Server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.timestream-for-influxdb-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22AWS_PROFILE%22%3A%22your-aws-profile%22%2C%22AWS_REGION%22%3A%22us-east-1%22%2C%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%7D%2C%22disabled%22%3Afalse%2C%22autoApprove%22%3A%5B%5D%7D) |
| [AWS S3 Tables MCP Server](src/s3-tables-mcp-server) | 최적화된 분석을 위한 S3 Tables 관리 | [![Install](https://img.shields.io/badge/Install-Kiro-9046FF?style=flat-square&logo=kiro)](https://kiro.dev/launch/mcp/add?name=awslabs.s3-tables-mcp-server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.s3-tables-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22AWS_PROFILE%22%3A%22your-aws-profile%22%2C%22AWS_REGION%22%3A%22us-east-1%22%7D%7D) <br/>[![Install](https://img.shields.io/badge/Install-Cursor-blue?style=flat-square&logo=cursor)](https://cursor.com/en/install-mcp?name=awslabs.s3-tables-mcp-server&config=eyJjb21tYW5kIjoidXZ4IGF3c2xhYnMuczMtdGFibGVzLW1jcC1zZXJ2ZXJAbGF0ZXN0IiwiZW52Ijp7IkFXU19QUk9GSUxFIjoieW91ci1hd3MtcHJvZmlsZSIsIkFXU19SRUdJT04iOiJ1cy1lYXN0LTEifX0%3D) <br/>[![Install on VS Code](https://img.shields.io/badge/Install-VS_Code-FF9900?style=flat-square&logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/redirect/mcp/install?name=S3%20Tables%20MCP%20Server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.s3-tables-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22AWS_PROFILE%22%3A%22your-aws-profile%22%2C%22AWS_REGION%22%3A%22us-east-1%22%7D%7D) |
| [Amazon Redshift MCP Server](src/redshift-mcp-server) | 데이터 웨어하우스 작업 및 분석 쿼리 | [![Install](https://img.shields.io/badge/Install-Kiro-9046FF?style=flat-square&logo=kiro)](https://kiro.dev/launch/mcp/add?name=awslabs.redshift-mcp-server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.redshift-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22AWS_PROFILE%22%3A%22default%22%2C%22AWS_REGION%22%3A%22us-east-1%22%2C%22FASTMCP_LOG_LEVEL%22%3A%22INFO%22%7D%7D) <br/>[![Install](https://img.shields.io/badge/Install-Cursor-blue?style=flat-square&logo=cursor)](https://cursor.com/en/install-mcp?name=awslabs.redshift-mcp-server&config=eyJjb21tYW5kIjoidXZ4IGF3c2xhYnMucmVkc2hpZnQtbWNwLXNlcnZlckBsYXRlc3QiLCJlbnYiOnsiQVdTX1BST0ZJTEUiOiJkZWZhdWx0IiwiQVdTX1JFR0lPTiI6InVzLWVhc3QtMSIsIkZBU1RNQ1BfTE9HX0xFVkVMIjoiSU5GTyJ9LCJkaXNhYmxlZCI6ZmFsc2UsImF1dG9BcHByb3ZlIjpbXX0%3D) <br/>[![Install on VS Code](https://img.shields.io/badge/Install-VS_Code-FF9900?style=flat-square&logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/redirect/mcp/install?name=Redshift%20MCP%20Server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.redshift-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22AWS_PROFILE%22%3A%22default%22%2C%22AWS_REGION%22%3A%22us-east-1%22%2C%22FASTMCP_LOG_LEVEL%22%3A%22INFO%22%7D%2C%22disabled%22%3Afalse%2C%22autoApprove%22%3A%5B%5D%7D) |
| [Amazon RDS Oracle MCP Server](src/oracle-mcp-server) | Secrets Manager 인증을 통한 Oracle Database 작업 | [![Install](https://img.shields.io/badge/Install-Kiro-9046FF?style=flat-square&logo=kiro)](https://kiro.dev/launch/mcp/add?name=awslabs.oracle-mcp-server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.oracle-mcp-server%40latest%22%2C%22--db_endpoint%22%2C%22%5Byour%20data%5D%22%2C%22--secret_arn%22%2C%22%5Byour%20data%5D%22%2C%22--database%22%2C%22%5Byour%20data%5D%22%2C%22--region%22%2C%22%5Byour%20data%5D%22%5D%2C%22env%22%3A%7B%22AWS_PROFILE%22%3A%22your-aws-profile%22%2C%22AWS_REGION%22%3A%22us-east-1%22%2C%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%7D%7D) <br/>[![Install](https://img.shields.io/badge/Install-Cursor-blue?style=flat-square&logo=cursor)](https://cursor.com/en/install-mcp?name=awslabs.oracle-mcp-server&config=eyJjb21tYW5kIjogInV2eCBhd3NsYWJzLm9yYWNsZS1tY3Atc2VydmVyQGxhdGVzdCAtLWRiX2VuZHBvaW50IFt5b3VyIGRhdGFdIC0tc2VjcmV0X2FybiBbeW91ciBkYXRhXSAtLWRhdGFiYXNlIFt5b3VyIGRhdGFdIC0tcmVnaW9uIFt5b3VyIGRhdGFdIiwgImVudiI6IHsiQVdTX1BST0ZJTEUiOiAieW91ci1hd3MtcHJvZmlsZSIsICJBV1NfUkVHSU9OIjogInVzLWVhc3QtMSIsICJGQVNUTUNQX0xPR19MRVZFTCI6ICJFUlJPUiJ9LCAiZGlzYWJsZWQiOiBmYWxzZSwgImF1dG9BcHByb3ZlIjogW119) <br/>[![Install on VS Code](https://img.shields.io/badge/Install-VS_Code-FF9900?style=flat-square&logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/redirect/mcp/install?name=Oracle%20MCP%20Server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.oracle-mcp-server%40latest%22%2C%22--db_endpoint%22%2C%22%5Byour%20data%5D%22%2C%22--secret_arn%22%2C%22%5Byour%20data%5D%22%2C%22--database%22%2C%22%5Byour%20data%5D%22%2C%22--region%22%2C%22%5Byour%20data%5D%22%5D%2C%22env%22%3A%7B%22AWS_PROFILE%22%3A%22your-aws-profile%22%2C%22AWS_REGION%22%3A%22us-east-1%22%2C%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%7D%2C%22disabled%22%3Afalse%2C%22autoApprove%22%3A%5B%5D%7D) |
| [AWS IoT SiteWise MCP Server](src/aws-iot-sitewise-mcp-server) | 산업용 IoT 자산 관리, 데이터 수집, 분석 | [![Install](https://img.shields.io/badge/Install-Kiro-9046FF?style=flat-square&logo=kiro)](https://kiro.dev/launch/mcp/add?name=awslabs.aws-iot-sitewise-mcp-server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.aws-iot-sitewise-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22AWS_PROFILE%22%3A%22your-aws-profile%22%2C%22AWS_REGION%22%3A%22us-east-1%22%2C%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%7D%7D) <br/>[![Install](https://img.shields.io/badge/Install-Cursor-blue?style=flat-square&logo=cursor)](https://cursor.com/en/install-mcp?name=awslabs.aws-iot-sitewise-mcp-server&config=eyJjb21tYW5kIjoidXZ4IGF3c2xhYnMuYXdzLWlvdC1zaXRld2lzZS1tY3Atc2VydmVyQGxhdGVzdCIsImVudiI6eyJBV1NfUFJPRklMRSI6InlvdXItYXdzLXByb2ZpbGUiLCJBV1NfUkVHSU9OIjoidXMtZWFzdC0xIiwiRkFTVE1DUF9MT0dfTEVWRUwiOiJFUlJPUiJ9LCJkaXNhYmxlZCI6ZmFsc2UsImF1dG9BcHByb3ZlIjpbXX0%3D) <br/>[![Install on VS Code](https://img.shields.io/badge/Install-VS_Code-FF9900?style=flat-square&logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/redirect/mcp/install?name=AWS%20IoT%20SiteWise%20MCP%20Server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.aws-iot-sitewise-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22AWS_PROFILE%22%3A%22your-aws-profile%22%2C%22AWS_REGION%22%3A%22us-east-1%22%2C%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%7D%2C%22disabled%22%3Afalse%2C%22autoApprove%22%3A%5B%5D%7D) |
| [Amazon RDS MSSQL MCP Server](src/mssql-mcp-server)                                 | RDS Data API를 통한 SQL Server 데이터베이스 작업 | [![Install](https://img.shields.io/badge/Install-Kiro-9046FF?style=flat-square&logo=kiro)](https://kiro.dev/launch/mcp/add?name=awslabs.mssql-mcp-server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.mssql-mcp-server%40latest%22%2C%22--resource_arn%22%2C%22%5Byour%22%2C%22data%5D%22%2C%22--secret_arn%22%2C%22%5Byour%22%2C%22data%5D%22%2C%22--database%22%2C%22%5Byour%22%2C%22data%5D%22%2C%22--region%22%2C%22%5Byour%22%2C%22data%5D%22%2C%22--readonly%22%2C%22True%22%5D%2C%22env%22%3A%7B%22AWS_PROFILE%22%3A%22your-aws-profile%22%2C%22AWS_REGION%22%3A%22us-east-1%22%2C%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%7D%7D) <br/>[![Install](https://img.shields.io/badge/Install-Cursor-blue?style=flat-square&logo=cursor)](https://cursor.com/en/install-mcp?name=awslabs.mssql-mcp-server&config=eyJjb21tYW5kIjoidXZ4IGF3c2xhYnMubXNzcWwtbWNwLXNlcnZlckBsYXRlc3QgLS1yZXNvdXJjZV9hcm4gW3lvdXIgZGF0YV0gLS1zZWNyZXRfYXJuIFt5b3VyIGRhdGFdIC0tZGF0YWJhc2UgW3lvdXIgZGF0YV0gLS1yZWdpb24gW3lvdXIgZGF0YV0gLS1yZWFkb25seSBUcnVlIiwiZW52Ijp7IkFXU19QUk9GSUxFIjoieW91ci1hd3MtcHJvZmlsZSIsIkFXU19SRUdJT04iOiJ1cy1lYXN0LTEiLCJGQVNUTUNQX0xPR19MRVZFTCI6IkVSUk9SIn0sImRpc2FibGVkIjpmYWxzZSwiYXV0b0FwcHJvdmUiOltdJSAgICAgICAK%3D%3D) <br/>[![Install on VS Code](https://img.shields.io/badge/Install-VS_Code-FF9900?style=flat-square&logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/redirect/mcp/install?name=MSSQL%20MCP%20Server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.mssql-mcp-server%40latest%22%2C%22--resource_arn%22%2C%22%5Byour%20data%5D%22%2C%22--secret_arn%22%2C%22%5Byour%20data%5D%22%2C%22--database%22%2C%22%5Byour%20data%5D%22%2C%22--region%22%2C%22%5Byour%20data%5D%22%2C%22--readonly%22%2C%22True%22%5D%2C%22env%22%3A%7B%22AWS_PROFILE%22%3A%22your-aws-profile%22%2C%22AWS_REGION%22%3A%22us-east-1%22%2C%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%7D%2C%22disabled%22%3Afalse%2C%22autoApprove%22%3A%5B%5D%7D) |

##### 검색 및 분석

- **[Amazon OpenSearch MCP Server](https://github.com/opensearch-project/opensearch-mcp-server-py)** - OpenSearch 기반 검색, 분석, 옵저버빌리티

#### 백엔드 API 제공자
| 서버 이름 | 설명 | 설치 |
|-------------|-------------|---------|
| [AWS AppSync MCP Server](src/aws-appsync-mcp-server) | AWS AppSync 기반 애플리케이션 백엔드 관리 및 상호 작용 | [![Install](https://img.shields.io/badge/Install-Kiro-9046FF?style=flat-square&logo=kiro)](https://kiro.dev/launch/mcp/add?name=awslabs.aws-appsync-mcp-server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.aws-appsync-mcp-server%40latest%22%2C%22--allow-write%22%5D%2C%22env%22%3A%7B%22AWS_PROFILE%22%3A%22default%22%2C%22AWS_REGION%22%3A%22us-east-1%22%2C%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%7D%7D) <br/>[![Install](https://img.shields.io/badge/Install-Cursor-blue?style=flat-square&logo=cursor)](https://cursor.com/en/install-mcp?name=awslabs.aws-appsync-mcp-server&config=eyJjb21tYW5kIjoidXZ4IGF3c2xhYnMuYXdzLWFwcHN5bmMtbWNwLXNlcnZlckBsYXRlc3QgLS1hbGxvdy13cml0ZSIsImVudiI6eyJBV1NfUFJPRklMRSI6ImRlZmF1bHQiLCJBV1NfUkVHSU9OIjoidXMtZWFzdC0xIiwiRkFTVE1DUF9MT0dfTEVWRUwiOiJFUlJPUiJ9LCJkaXNhYmxlZCI6ZmFsc2UsImF1dG9BcHByb3ZlIjpbXX0=) <br/>[![Install on VS Code](https://img.shields.io/badge/Install-VS_Code-FF9900?style=flat-square&logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/redirect/mcp/install?name=AWS%20AppSync%20MCP%20Server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.aws-appsync-mcp-server%40latest%22%2C%20%22--allow-write%22%5D%2C%22env%22%3A%7B%22AWS_PROFILE%22%3A%22default%22%2C%22AWS_REGION%22%3A%22us-east-1%22%2C%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%7D%2C%22disabled%22%3Afalse%2C%22autoApprove%22%3A%5B%5D%7D) |

#### 캐싱 및 성능
| 서버 이름 | 설명 | 설치 |
|-------------|-------------|---------|
| [Amazon ElastiCache MCP Server](src/elasticache-mcp-server) | ElastiCache 컨트롤 플레인 전체 작업 | [![Install](https://img.shields.io/badge/Install-Kiro-9046FF?style=flat-square&logo=kiro)](https://kiro.dev/launch/mcp/add?name=awslabs.elasticache-mcp-server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.elasticache-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22AWS_PROFILE%22%3A%22default%22%2C%22AWS_REGION%22%3A%22us-west-2%22%2C%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%7D%7D) <br/>[![Install](https://img.shields.io/badge/Install-Cursor-blue?style=flat-square&logo=cursor)](https://cursor.com/en/install-mcp?name=awslabs.elasticache-mcp-server&config=eyJjb21tYW5kIjoidXZ4IGF3c2xhYnMuZWxhc3RpY2FjaGUtbWNwLXNlcnZlckBsYXRlc3QiLCJlbnYiOnsiQVdTX1BST0ZJTEUiOiJkZWZhdWx0IiwiQVdTX1JFR0lPTiI6InVzLXdlc3QtMiIsIkZBU1RNQ1BfTE9HX0xFVkVMIjoiRVJST1IifSwiZGlzYWJsZWQiOmZhbHNlLCJhdXRvQXBwcm92ZSI6W119) <br/>[![Install on VS Code](https://img.shields.io/badge/Install-VS_Code-FF9900?style=flat-square&logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/redirect/mcp/install?name=ElastiCache%20MCP%20Server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.elasticache-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22AWS_PROFILE%22%3A%22default%22%2C%22AWS_REGION%22%3A%22us-west-2%22%2C%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%7D%2C%22disabled%22%3Afalse%2C%22autoApprove%22%3A%5B%5D%7D) |
| [Amazon ElastiCache / MemoryDB for Valkey MCP Server](src/valkey-mcp-server) | Valkey를 활용한 고급 데이터 구조 및 캐싱 | [![Install](https://img.shields.io/badge/Install-Kiro-9046FF?style=flat-square&logo=kiro)](https://kiro.dev/launch/mcp/add?name=awslabs.valkey-mcp-server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.valkey-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22VALKEY_HOST%22%3A%22127.0.0.1%22%2C%22VALKEY_PORT%22%3A%226379%22%2C%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%7D%7D) <br/>[![Install](https://img.shields.io/badge/Install-Cursor-blue?style=flat-square&logo=cursor)](https://cursor.com/en/install-mcp?name=awslabs.valkey-mcp-server&config=eyJjb21tYW5kIjoidXZ4IGF3c2xhYnMudmFsa2V5LW1jcC1zZXJ2ZXJAbGF0ZXN0IiwiZW52Ijp7IlZBTEtFWV9IT1NUIjoiMTI3LjAuMC4xIiwiVkFMS0VZX1BPUlQiOiI2Mzc5IiwiRkFTVE1DUF9MT0dfTEVWRUwiOiJFUlJPUiJ9LCJhdXRvQXBwcm92ZSI6W10sImRpc2FibGVkIjpmYWxzZX0%3D) <br/>[![Install on VS Code](https://img.shields.io/badge/Install-VS_Code-FF9900?style=flat-square&logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/redirect/mcp/install?name=Valkey%20MCP%20Server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.valkey-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22VALKEY_HOST%22%3A%22127.0.0.1%22%2C%22VALKEY_PORT%22%3A%226379%22%2C%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%7D%2C%22autoApprove%22%3A%5B%5D%2C%22disabled%22%3Afalse%7D) |
| [Amazon ElastiCache for Memcached MCP Server](src/memcached-mcp-server) | Memcached 프로토콜을 사용한 고속 캐싱 | [![Install](https://img.shields.io/badge/Install-Kiro-9046FF?style=flat-square&logo=kiro)](https://kiro.dev/launch/mcp/add?name=awslabs.memcached-mcp-server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.memcached-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%2C%22MEMCACHED_HOST%22%3A%22your-memcached-host%22%2C%22MEMCACHED_PORT%22%3A%2211211%22%7D%7D) <br/>[![Install](https://img.shields.io/badge/Install-Cursor-blue?style=flat-square&logo=cursor)](https://cursor.com/en/install-mcp?name=awslabs.memcached-mcp-server&config=eyJjb21tYW5kIjoidXZ4IGF3c2xhYnMubWVtY2FjaGVkLW1jcC1zZXJ2ZXJAbGF0ZXN0IiwiZW52Ijp7IkZBU1RNQ1BfTE9HX0xFVkVMIjoiRVJST1IiLCJNRU1DQUNIRURfSE9TVCI6InlvdXItbWVtY2FjaGVkLWhvc3QiLCJNRU1DQUNIRURfUE9SVCI6IjExMjExIn0sImRpc2FibGVkIjpmYWxzZSwiYXV0b0FwcHJvdmUiOltdfQ%3D%3D) <br/>[![Install on VS Code](https://img.shields.io/badge/Install-VS_Code-FF9900?style=flat-square&logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/redirect/mcp/install?name=Memcached%20MCP%20Server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.memcached-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%2C%22MEMCACHED_HOST%22%3A%22your-memcached-host%22%2C%22MEMCACHED_PORT%22%3A%2211211%22%7D%2C%22disabled%22%3Afalse%2C%22autoApprove%22%3A%5B%5D%7D) |

#### 오픈 데이터

| 서버 이름 | 설명 | 설치 |
|-------------|-------------|---------|
| [Registry of Open Data (RODA) MCP Server](src/roda-mcp-server) | AWS의 오픈 데이터셋 검색, 탐색, 미리 보기 | [![Install](https://img.shields.io/badge/Install-Kiro-9046FF?style=flat-square&logo=kiro)](https://kiro.dev/launch/mcp/add?name=awslabs.roda-mcp-server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.roda-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%7D%7D) <br/>[![Install](https://img.shields.io/badge/Install-Cursor-blue?style=flat-square&logo=cursor)](https://cursor.com/en/install-mcp?name=awslabs.roda-mcp-server&config=eyJjb21tYW5kIjoidXZ4IGF3c2xhYnMucm9kYS1tY3Atc2VydmVyQGxhdGVzdCIsImVudiI6eyJGQVNUTUNQX0xPR19MRVZFTCI6IkVSUk9SIn0sImRpc2FibGVkIjpmYWxzZSwiYXV0b0FwcHJvdmUiOltdfQ==) <br/>[![Install on VS Code](https://img.shields.io/badge/Install-VS_Code-FF9900?style=flat-square&logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/redirect/mcp/install?name=RODA%20MCP%20Server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.roda-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%7D%2C%22disabled%22%3Afalse%2C%22autoApprove%22%3A%5B%5D%7D) |


### 🛠️ 개발자 도구 및 지원
코드 분석, 문서화, 테스트 유틸리티로 개발을 가속합니다.

| 서버 이름 | 설명 | 설치 |
|-------------|-------------|---------|
| [AWS IAM MCP Server](src/iam-mcp-server) | 보안 모범 사례를 반영한 IAM 사용자, 역할, 그룹, 정책의 포괄적 관리 | [![Install](https://img.shields.io/badge/Install-Kiro-9046FF?style=flat-square&logo=kiro)](https://kiro.dev/launch/mcp/add?name=awslabs.iam-mcp-server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.iam-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22AWS_PROFILE%22%3A%22your-aws-profile%22%2C%22AWS_REGION%22%3A%22us-east-1%22%2C%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%7D%7D) <br/>[![Install](https://img.shields.io/badge/Install-Cursor-blue?style=flat-square&logo=cursor)](https://cursor.com/en/install-mcp?name=awslabs.iam-mcp-server&config=eyJjb21tYW5kIjoidXZ4IiwiYXJncyI6WyJhd3NsYWJzLmlhbS1tY3Atc2VydmVyQGxhdGVzdCJdLCJlbnYiOnsiQVdTX1BST0ZJTEUiOiJ5b3VyLWF3cy1wcm9maWxlIiwiQVdTX1JFR0lPTiI6InVzLWVhc3QtMSIsIkZBU1RNQ1BfTE9HX0xFVkVMIjoiRVJST1IifX0%3D) <br/>[![Install on VS Code](https://img.shields.io/badge/Install-VS_Code-FF9900?style=flat-square&logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/redirect/mcp/install?name=AWS%20IAM%20MCP%20Server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.iam-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22AWS_PROFILE%22%3A%22your-aws-profile%22%2C%22AWS_REGION%22%3A%22us-east-1%22%2C%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%7D%7D) |
| [AWS Security Agent MCP Server](src/security-agent-mcp-server) | AWS Security Agent를 활용한 자동화된 보안 스캐닝, 침투 테스트, 조치 | |
| [OpenAPI MCP Server](src/openapi-mcp-server) | OpenAPI 명세를 통한 동적 API 통합 | [![Install](https://img.shields.io/badge/Install-Kiro-9046FF?style=flat-square&logo=kiro)](https://kiro.dev/launch/mcp/add?name=awslabs.openapi-mcp-server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.openapi-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22API_NAME%22%3A%22your-api-name%22%2C%22API_BASE_URL%22%3A%22https%3A//api.example.com%22%2C%22API_SPEC_URL%22%3A%22https%3A//api.example.com/openapi.json%22%2C%22LOG_LEVEL%22%3A%22ERROR%22%2C%22ENABLE_PROMETHEUS%22%3A%22false%22%2C%22ENABLE_OPERATION_PROMPTS%22%3A%22true%22%2C%22UVICORN_TIMEOUT_GRACEFUL_SHUTDOWN%22%3A%225.0%22%2C%22UVICORN_GRACEFUL_SHUTDOWN%22%3A%22true%22%7D%7D) <br/>[![Install](https://img.shields.io/badge/Install-Cursor-blue?style=flat-square&logo=cursor)](https://cursor.com/en/install-mcp?name=awslabs.openapi-mcp-server&config=eyJjb21tYW5kIjoidXZ4IGF3c2xhYnMub3BlbmFwaS1tY3Atc2VydmVyQGxhdGVzdCIsImVudiI6eyJBUElfTkFNRSI6InlvdXItYXBpLW5hbWUiLCJBUElfQkFTRV9VUkwiOiJodHRwczovL2FwaS5leGFtcGxlLmNvbSIsIkFQSV9TUEVDX1VSTCI6Imh0dHBzOi8vYXBpLmV4YW1wbGUuY29tL29wZW5hcGkuanNvbiIsIkxPR19MRVZFTCI6IkVSUk9SIiwiRU5BQkxFX1BST01FVEhFVVMiOiJmYWxzZSIsIkVOQUJMRV9PUEVSQVRJT05fUFJPTVBUUyI6InRydWUiLCJVVklDT1JOX1RJTUVPVVRfR1JBQ0VGVUxfU0hVVERPV04iOiI1LjAiLCJVVklDT1JOX0dSQUNFRlVMX1NIVVRET1dOIjoidHJ1ZSJ9LCJkaXNhYmxlZCI6ZmFsc2UsImF1dG9BcHByb3ZlIjpbXX0%3D) <br/>[![Install on VS Code](https://img.shields.io/badge/Install-VS_Code-FF9900?style=flat-square&logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/redirect/mcp/install?name=OpenAPI%20MCP%20Server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.openapi-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22API_NAME%22%3A%22your-api-name%22%2C%22API_BASE_URL%22%3A%22https%3A%2F%2Fapi.example.com%22%2C%22API_SPEC_URL%22%3A%22https%3A%2F%2Fapi.example.com%2Fopenapi.json%22%2C%22LOG_LEVEL%22%3A%22ERROR%22%2C%22ENABLE_PROMETHEUS%22%3A%22false%22%2C%22ENABLE_OPERATION_PROMPTS%22%3A%22true%22%2C%22UVICORN_TIMEOUT_GRACEFUL_SHUTDOWN%22%3A%225.0%22%2C%22UVICORN_GRACEFUL_SHUTDOWN%22%3A%22true%22%7D%2C%22disabled%22%3Afalse%2C%22autoApprove%22%3A%5B%5D%7D) |


### 📡 통합 및 메시징

메시징, 워크플로, 위치 서비스로 시스템을 연결합니다.

| 서버 이름 | 설명 | 설치 |
|-------------|-------------|---------|
| [Amazon SNS / SQS MCP Server](src/amazon-sns-sqs-mcp-server) | 이벤트 기반 메시징 및 큐 관리 | [![Install](https://img.shields.io/badge/Install-Kiro-9046FF?style=flat-square&logo=kiro)](https://kiro.dev/launch/mcp/add?name=awslabs.amazon-sns-sqs-mcp-server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.amazon-sns-sqs-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22AWS_PROFILE%22%3A%22your-aws-profile%22%2C%22AWS_REGION%22%3A%22us-east-1%22%7D%7D) <br/>[![Install](https://img.shields.io/badge/Install-Cursor-blue?style=flat-square&logo=cursor)](https://cursor.com/en/install-mcp?name=awslabs.amazon-sns-sqs-mcp-server&config=eyJjb21tYW5kIjoidXZ4IGF3c2xhYnMuYW1hem9uLXNucy1zcXMtbWNwLXNlcnZlckBsYXRlc3QiLCJlbnYiOnsiQVdTX1BST0ZJTEUiOiJ5b3VyLWF3cy1wcm9maWxlIiwiQVdTX1JFR0lPTiI6InVzLWVhc3QtMSJ9fQ%3D%3D) <br/>[![Install on VS Code](https://img.shields.io/badge/Install-VS_Code-FF9900?style=flat-square&logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/redirect/mcp/install?name=Amazon%20SNS%2FSQS%20MCP%20Server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.amazon-sns-sqs-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22AWS_PROFILE%22%3A%22your-aws-profile%22%2C%22AWS_REGION%22%3A%22us-east-1%22%7D%7D) |
| [Amazon MQ MCP Server](src/amazon-mq-mcp-server) | RabbitMQ 및 ActiveMQ 메시지 브로커 관리 | [![Install](https://img.shields.io/badge/Install-Kiro-9046FF?style=flat-square&logo=kiro)](https://kiro.dev/launch/mcp/add?name=awslabs.amazon-mq-mcp-server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.amazon-mq-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22AWS_PROFILE%22%3A%22your-aws-profile%22%2C%22AWS_REGION%22%3A%22us-east-1%22%2C%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%7D%7D) <br/>[![Install](https://img.shields.io/badge/Install-Cursor-blue?style=flat-square&logo=cursor)](https://cursor.com/en/install-mcp?name=awslabs.amazon-mq-mcp-server&config=eyJjb21tYW5kIjoidXZ4IGF3c2xhYnMuYW1hem9uLW1xLW1jcC1zZXJ2ZXJAbGF0ZXN0IiwiZW52Ijp7IkFXU19QUk9GSUxFIjoieW91ci1hd3MtcHJvZmlsZSIsIkFXU19SRUdJT04iOiJ1cy1lYXN0LTEiLCJGQVNUTUNQX0xPR19MRVZFTCI6IkVSUk9SIn0sImRpc2FibGVkIjpmYWxzZSwiYXV0b0FwcHJvdmUiOltdfQ%3D%3D) <br/>[![Install on VS Code](https://img.shields.io/badge/Install-VS_Code-FF9900?style=flat-square&logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/redirect/mcp/install?name=Amazon%20MQ%20MCP%20Server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.amazon-mq-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22AWS_PROFILE%22%3A%22your-aws-profile%22%2C%22AWS_REGION%22%3A%22us-east-1%22%2C%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%7D%2C%22disabled%22%3Afalse%2C%22autoApprove%22%3A%5B%5D%7D) |
| [AWS Step Functions Tool MCP Server](src/stepfunctions-tool-mcp-server) | 복잡한 워크플로 및 비즈니스 프로세스 실행 | [![Install](https://img.shields.io/badge/Install-Kiro-9046FF?style=flat-square&logo=kiro)](https://kiro.dev/launch/mcp/add?name=awslabs.stepfunctions-tool-mcp-server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.stepfunctions-tool-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22AWS_PROFILE%22%3A%22your-aws-profile%22%2C%22AWS_REGION%22%3A%22us-east-1%22%2C%22STATE_MACHINE_PREFIX%22%3A%22your-state-machine-prefix%22%2C%22STATE_MACHINE_LIST%22%3A%22your-first-state-machine%2C%20your-second-state-machine%22%2C%22STATE_MACHINE_TAG_KEY%22%3A%22your-tag-key%22%2C%22STATE_MACHINE_TAG_VALUE%22%3A%22your-tag-value%22%2C%22STATE_MACHINE_INPUT_SCHEMA_ARN_TAG_KEY%22%3A%22your-state-machine-tag-for-input-schema%22%7D%7D) <br/>[![Install](https://img.shields.io/badge/Install-Cursor-blue?style=flat-square&logo=cursor)](https://cursor.com/en/install-mcp?name=awslabs.stepfunctions-tool-mcp-server&config=eyJjb21tYW5kIjoidXZ4IGF3c2xhYnMuc3RlcGZ1bmN0aW9ucy10b29sLW1jcC1zZXJ2ZXJAbGF0ZXN0IiwiZW52Ijp7IkFXU19QUk9GSUxFIjoieW91ci1hd3MtcHJvZmlsZSIsIkFXU19SRUdJT04iOiJ1cy1lYXN0LTEiLCJTVEFURV9NQUNISU5FX1BSRUZJWCI6InlvdXItc3RhdGUtbWFjaGluZS1wcmVmaXgiLCJTVEFURV9NQUNISU5FX0xJU1QiOiJ5b3VyLWZpcnN0LXN0YXRlLW1hY2hpbmUsIHlvdXItc2Vjb25kLXN0YXRlLW1hY2hpbmUiLCJTVEFURV9NQUNISU5FX1RBR19LRVkiOiJ5b3VyLXRhZy1rZXkiLCJTVEFURV9NQUNISU5FX1RBR19WQUxVRSI6InlvdXItdGFnLXZhbHVlIiwiU1RBVEVfTUFDSElORV9JTlBVVF9TQ0hFTUFfQVJOX1RBR19LRVkiOiJ5b3VyLXN0YXRlLW1hY2hpbmUtdGFnLWZvci1pbnB1dC1zY2hlbWEifX0%3D) <br/>[![Install on VS Code](https://img.shields.io/badge/Install-VS_Code-FF9900?style=flat-square&logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/redirect/mcp/install?name=Step%20Functions%20Tool%20MCP%20Server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.stepfunctions-tool-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22AWS_PROFILE%22%3A%22your-aws-profile%22%2C%22AWS_REGION%22%3A%22us-east-1%22%2C%22STATE_MACHINE_PREFIX%22%3A%22your-state-machine-prefix%22%2C%22STATE_MACHINE_LIST%22%3A%22your-first-state-machine%2C%20your-second-state-machine%22%2C%22STATE_MACHINE_TAG_KEY%22%3A%22your-tag-key%22%2C%22STATE_MACHINE_TAG_VALUE%22%3A%22your-tag-value%22%2C%22STATE_MACHINE_INPUT_SCHEMA_ARN_TAG_KEY%22%3A%22your-state-machine-tag-for-input-schema%22%7D%2C%22disabled%22%3Afalse%2C%22autoApprove%22%3A%5B%5D%7D) |
| [Amazon Location Service MCP Server](src/aws-location-mcp-server) | 장소 검색, 지오코딩, 경로 최적화 | [![Install](https://img.shields.io/badge/Install-Kiro-9046FF?style=flat-square&logo=kiro)](https://kiro.dev/launch/mcp/add?name=awslabs.aws-location-mcp-server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.aws-location-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22AWS_PROFILE%22%3A%22your-aws-profile%22%2C%22AWS_REGION%22%3A%22us-east-1%22%2C%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%7D%7D) <br/>[![Install](https://img.shields.io/badge/Install-Cursor-blue?style=flat-square&logo=cursor)](https://cursor.com/en/install-mcp?name=awslabs.aws-location-mcp-server&config=eyJjb21tYW5kIjoidXZ4IGF3c2xhYnMuYXdzLWxvY2F0aW9uLW1jcC1zZXJ2ZXJAbGF0ZXN0IiwiZW52Ijp7IkFXU19QUk9GSUxFIjoieW91ci1hd3MtcHJvZmlsZSIsIkFXU19SRUdJT04iOiJ1cy1lYXN0LTEiLCJGQVNUTUNQX0xPR19MRVZFTCI6IkVSUk9SIn0sImRpc2FibGVkIjpmYWxzZSwiYXV0b0FwcHJvdmUiOltdfQ%3D%3D) <br/>[![Install on VS Code](https://img.shields.io/badge/Install-VS_Code-FF9900?style=flat-square&logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/redirect/mcp/install?name=AWS%20Location%20MCP%20Server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.aws-location-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22AWS_PROFILE%22%3A%22your-aws-profile%22%2C%22AWS_REGION%22%3A%22us-east-1%22%2C%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%7D%2C%22disabled%22%3Afalse%2C%22autoApprove%22%3A%5B%5D%7D) |
| [OpenAPI MCP Server](src/openapi-mcp-server) | OpenAPI 명세를 통한 동적 API 통합 | [![Install](https://img.shields.io/badge/Install-Kiro-9046FF?style=flat-square&logo=kiro)](https://kiro.dev/launch/mcp/add?name=awslabs.openapi-mcp-server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.openapi-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22API_NAME%22%3A%22your-api-name%22%2C%22API_BASE_URL%22%3A%22https%3A//api.example.com%22%2C%22API_SPEC_URL%22%3A%22https%3A//api.example.com/openapi.json%22%2C%22LOG_LEVEL%22%3A%22ERROR%22%2C%22ENABLE_PROMETHEUS%22%3A%22false%22%2C%22ENABLE_OPERATION_PROMPTS%22%3A%22true%22%2C%22UVICORN_TIMEOUT_GRACEFUL_SHUTDOWN%22%3A%225.0%22%2C%22UVICORN_GRACEFUL_SHUTDOWN%22%3A%22true%22%7D%7D) <br/>[![Install](https://img.shields.io/badge/Install-Cursor-blue?style=flat-square&logo=cursor)](https://cursor.com/en/install-mcp?name=awslabs.openapi-mcp-server&config=eyJjb21tYW5kIjoidXZ4IGF3c2xhYnMub3BlbmFwaS1tY3Atc2VydmVyQGxhdGVzdCIsImVudiI6eyJBUElfTkFNRSI6InlvdXItYXBpLW5hbWUiLCJBUElfQkFTRV9VUkwiOiJodHRwczovL2FwaS5leGFtcGxlLmNvbSIsIkFQSV9TUEVDX1VSTCI6Imh0dHBzOi8vYXBpLmV4YW1wbGUuY29tL29wZW5hcGkuanNvbiIsIkxPR19MRVZFTCI6IkVSUk9SIiwiRU5BQkxFX1BST01FVEhFVVMiOiJmYWxzZSIsIkVOQUJMRV9PUEVSQVRJT05fUFJPTVBUUyI6InRydWUiLCJVVklDT1JOX1RJTUVPVVRfR1JBQ0VGVUxfU0hVVERPV04iOiI1LjAiLCJVVklDT1JOX0dSQUNFRlVMX1NIVVRET1dOIjoidHJ1ZSJ9LCJkaXNhYmxlZCI6ZmFsc2UsImF1dG9BcHByb3ZlIjpbXX0%3D) <br/>[![Install on VS Code](https://img.shields.io/badge/Install-VS_Code-FF9900?style=flat-square&logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/redirect/mcp/install?name=OpenAPI%20MCP%20Server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.openapi-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22API_NAME%22%3A%22your-api-name%22%2C%22API_BASE_URL%22%3A%22https%3A%2F%2Fapi.example.com%22%2C%22API_SPEC_URL%22%3A%22https%3A%2F%2Fapi.example.com%2Fopenapi.json%22%2C%22LOG_LEVEL%22%3A%22ERROR%22%2C%22ENABLE_PROMETHEUS%22%3A%22false%22%2C%22ENABLE_OPERATION_PROMPTS%22%3A%22true%22%2C%22UVICORN_TIMEOUT_GRACEFUL_SHUTDOWN%22%3A%225.0%22%2C%22UVICORN_GRACEFUL_SHUTDOWN%22%3A%22true%22%7D%2C%22disabled%22%3Afalse%2C%22autoApprove%22%3A%5B%5D%7D) |

### 💰 비용 및 운영

AWS 인프라와 비용을 모니터링, 최적화, 관리합니다.

| 서버 이름 | 설명 | 설치 |
|-------------|-------------|---------|
| [AWS Pricing MCP Server](src/aws-pricing-mcp-server) | AWS 서비스 요금 조회 및 비용 추정 | [![Install](https://img.shields.io/badge/Install-Kiro-9046FF?style=flat-square&logo=kiro)](https://kiro.dev/launch/mcp/add?name=awslabs.aws-pricing-mcp-server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.aws-pricing-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%2C%22AWS_PROFILE%22%3A%22your-aws-profile%22%2C%22AWS_REGION%22%3A%22us-east-1%22%7D%7D) <br/>[![Install](https://img.shields.io/badge/Install-Cursor-blue?style=flat-square&logo=cursor)](https://cursor.com/en/install-mcp?name=awslabs.aws-pricing-mcp-server&config=ewogICAgImNvbW1hbmQiOiAidXZ4IGF3c2xhYnMuYXdzLXByaWNpbmctbWNwLXNlcnZlckBsYXRlc3QiLAogICAgImVudiI6IHsKICAgICAgIkZBU1RNQ1BfTE9HX0xFVkVMIjogIkVSUk9SIiwKICAgICAgIkFXU19QUk9GSUxFIjogInlvdXItYXdzLXByb2ZpbGUiLAogICAgICAiQVdTX1JFR0lPTiI6ICJ1cy1lYXN0LTEiCiAgICB9LAogICAgImRpc2FibGVkIjogZmFsc2UsCiAgICAiYXV0b0FwcHJvdmUiOiBbXQogIH0K) <br/>[![Install on VS Code](https://img.shields.io/badge/Install-VS_Code-FF9900?style=flat-square&logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/redirect/mcp/install?name=AWS%20Pricing%20MCP%20Server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.aws-pricing-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%2C%22AWS_PROFILE%22%3A%22your-aws-profile%22%2C%22AWS_REGION%22%3A%22us-east-1%22%7D%2C%22disabled%22%3Afalse%2C%22autoApprove%22%3A%5B%5D%7D) |
| [Amazon CloudWatch MCP Server](src/cloudwatch-mcp-server) | 지표, 경보, 로그 분석 및 운영 트러블슈팅 | [![Install](https://img.shields.io/badge/Install-Kiro-9046FF?style=flat-square&logo=kiro)](https://kiro.dev/launch/mcp/add?name=awslabs.cloudwatch-mcp-server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.cloudwatch-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22AWS_PROFILE%22%3A%22%5BThe%20AWS%20Profile%20Name%20to%20use%20for%20AWS%20access%5D%22%2C%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%7D%7D) <br/>[![Install](https://img.shields.io/badge/Install-Cursor-blue?style=flat-square&logo=cursor)](https://cursor.com/en/install-mcp?name=awslabs.cloudwatch-mcp-server&config=ewogICAgImF1dG9BcHByb3ZlIjogW10sCiAgICAiZGlzYWJsZWQiOiBmYWxzZSwKICAgICJjb21tYW5kIjogInV2eCBhd3NsYWJzLmNsb3Vkd2F0Y2gtbWNwLXNlcnZlckBsYXRlc3QiLAogICAgImVudiI6IHsKICAgICAgIkFXU19QUk9GSUxFIjogIltUaGUgQVdTIFByb2ZpbGUgTmFtZSB0byB1c2UgZm9yIEFXUyBhY2Nlc3NdIiwKICAgICAgIkZBU1RNQ1BfTE9HX0xFVkVMIjogIkVSUk9SIgogICAgfSwKICAgICJ0cmFuc3BvcnRUeXBlIjogInN0ZGlvIgp9) <br/>[![Install on VS Code](https://img.shields.io/badge/Install-VS_Code-FF9900?style=flat-square&logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/redirect/mcp/install?name=CloudWatch%20MCP%20Server&config=%7B%22autoApprove%22%3A%5B%5D%2C%22disabled%22%3Afalse%2C%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.cloudwatch-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22AWS_PROFILE%22%3A%22%5BThe%20AWS%20Profile%20Name%20to%20use%20for%20AWS%20access%5D%22%2C%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%7D%2C%22transportType%22%3A%22stdio%22%7D) |
| [AWS Managed Prometheus MCP Server](src/prometheus-mcp-server) | Prometheus 호환 작업 | [![Install](https://img.shields.io/badge/Install-Kiro-9046FF?style=flat-square&logo=kiro)](https://kiro.dev/launch/mcp/add?name=awslabs.prometheus-mcp-server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.prometheus-mcp-server%40latest%22%2C%22--url%22%2C%22https%3A//aps-workspaces.us-east-1.amazonaws.com/workspaces/ws-%3CWorkspace%22%2C%22ID%3E%22%2C%22--region%22%2C%22%3CYour%22%2C%22AWS%22%2C%22Region%3E%22%2C%22--profile%22%2C%22%3CYour%22%2C%22CLI%22%2C%22Profile%22%2C%22%5Bdefault%5D%22%2C%22if%22%2C%22no%22%2C%22profile%22%2C%22is%22%2C%22used%3E%22%5D%2C%22env%22%3A%7B%22FASTMCP_LOG_LEVEL%22%3A%22DEBUG%22%2C%22AWS_PROFILE%22%3A%22%3CYour%20CLI%20Profile%20%5Bdefault%5D%20if%20no%20profile%20is%20used%3E%22%7D%7D) <br/>[![Install](https://img.shields.io/badge/Install-Cursor-blue?style=flat-square&logo=cursor)](https://cursor.com/en/install-mcp?name=awslabs.prometheus-mcp-server&config=eyJjb21tYW5kIjoidXZ4IGF3c2xhYnMucHJvbWV0aGV1cy1tY3Atc2VydmVyQGxhdGVzdCAtLXVybCBodHRwczovL2Fwcy13b3Jrc3BhY2VzLnVzLWVhc3QtMS5hbWF6b25hd3MuY29tL3dvcmtzcGFjZXMvd3MtPFdvcmtzcGFjZSBJRD4gLS1yZWdpb24gPFlvdXIgQVdTIFJlZ2lvbj4gLS1wcm9maWxlIDxZb3VyIENMSSBQcm9maWxlIFtkZWZhdWx0XSBpZiBubyBwcm9maWxlIGlzIHVzZWQ%2BIiwiZW52Ijp7IkZBU1RNQ1BfTE9HX0xFVkVMIjoiREVCVUciLCJBV1NfUFJPRklMRSI6IjxZb3VyIENMSSBQcm9maWxlIFtkZWZhdWx0XSBpZiBubyBwcm9maWxlIGlzIHVzZWQ%2BIn19) <br/>[![Install on VS Code](https://img.shields.io/badge/Install-VS_Code-FF9900?style=flat-square&logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/redirect/mcp/install?name=Prometheus%20MCP%20Server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.prometheus-mcp-server%40latest%22%2C%22--url%22%2C%22https%3A%2F%2Faps-workspaces.us-east-1.amazonaws.com%2Fworkspaces%2Fws-%3CWorkspace%20ID%3E%22%2C%22--region%22%2C%22%3CYour%20AWS%20Region%3E%22%2C%22--profile%22%2C%22%3CYour%20CLI%20Profile%20%5Bdefault%5D%20if%20no%20profile%20is%20used%3E%22%5D%2C%22env%22%3A%7B%22FASTMCP_LOG_LEVEL%22%3A%22DEBUG%22%2C%22AWS_PROFILE%22%3A%22%3CYour%20CLI%20Profile%20%5Bdefault%5D%20if%20no%20profile%20is%20used%3E%22%7D%7D) |
| [AWS Billing and Cost Management MCP Server](src/billing-cost-management-mcp-server/) | 청구 대상 및 견적(Proforma) 청구에 대한 결제 및 비용 관리 | [![Install](https://img.shields.io/badge/Install-Kiro-9046FF?style=flat-square&logo=kiro)](https://kiro.dev/launch/mcp/add?name=awslabs.billing-cost-management-mcp-server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.billing-cost-management-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%2C%22AWS_PROFILE%22%3A%22your-aws-profile%22%2C%22AWS_REGION%22%3A%22us-east-1%22%7D%7D) <br/>[![Install](https://img.shields.io/badge/Install-Cursor-blue?style=flat-square&logo=cursor)](https://cursor.com/en/install-mcp?name=awslabs.billing-cost-management-mcp-server&config=ewogICAgImNvbW1hbmQiOiAidXZ4IGF3c2xhYnMuYmlsbGluZy1jb3N0LW1hbmFnZW1lbnQtbWNwLXNlcnZlckBsYXRlc3QiLAogICAgImVudiI6IHsKICAgICAgIkZBU1RNQ1BfTE9HX0xFVkVMIjogIkVSUk9SIiwKICAgICAgIkFXU19QUk9GSUxFIjogInlvdXItYXdzLXByb2ZpbGUiLAogICAgICAiQVdTX1JFR0lPTiI6ICJ1cy1lYXN0LTEiCiAgICB9LAogICAgImRpc2FibGVkIjogZmFsc2UsCiAgICAiYXV0b0FwcHJvdmUiOiBbXQogIH0K) <br/>[![Install on VS Code](https://img.shields.io/badge/Install-VS_Code-FF9900?style=flat-square&logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/redirect/mcp/install?name=AWS%20Billing%20and%20Cost%20Management%20MCP%20Server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.billing-cost-management-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%2C%22AWS_PROFILE%22%3A%22your-aws-profile%22%2C%22AWS_REGION%22%3A%22us-east-1%22%7D%2C%22disabled%22%3Afalse%2C%22autoApprove%22%3A%5B%5D%7D) |

### 🧬 헬스케어 및 생명과학
AWS HealthAI 서비스와 상호 작용합니다.
| 서버 이름 | 설명 | 설치 |
|-------------|-------------|---------|
| [AWS HealthOmics MCP Server](src/aws-healthomics-mcp-server) | 생명과학 워크플로 생성, 실행, 디버깅, 최적화 | [![Install](https://img.shields.io/badge/Install-Kiro-9046FF?style=flat-square&logo=kiro)](https://kiro.dev/launch/mcp/add?name=awslabs.aws-healthomics-mcp-server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.aws-healthomics-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22AWS_REGION%22%3A%22us-east-1%22%2C%22AWS_PROFILE%22%3A%22your-profile%22%2C%22FASTMCP_LOG_LEVEL%22%3A%22WARNING%22%7D%7D) <br/>[![Install](https://img.shields.io/badge/Install-Cursor-blue?style=flat-square&logo=cursor)](https://cursor.com/en/install-mcp?name=awslabs.aws-healthomics-mcp-server&config=eyJjb21tYW5kIjoidXZ4IGF3c2xhYnMuYXdzLWhlYWx0aG9taWNzLW1jcC1zZXJ2ZXJAbGF0ZXN0IiwiZW52Ijp7IkFXU19SRUdJT04iOiJ1cy1lYXN0LTEiLCJBV1NfUFJPRklMRSI6InlvdXItcHJvZmlsZSIsIkZBU1RNQ1BfTE9HX0xFVkVMIjoiV0FSTklORyJ9fQ%3D%3D) <br/>[![Install on VS Code](https://img.shields.io/badge/Install-VS_Code-FF9900?style=flat-square&logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/redirect/mcp/install?name=AWS%20HealthOmics%20MCP%20Server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.aws-healthomics-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22AWS_REGION%22%3A%22us-east-1%22%2C%22AWS_PROFILE%22%3A%22your-profile%22%2C%22FASTMCP_LOG_LEVEL%22%3A%22WARNING%22%7D%7D) |
| [AWS HealthImaging MCP Server](src/healthimaging-mcp-server) | DICOM 작업, 데이터스토어 관리, 자동 검색을 위한 21개 도구로 의료 영상 데이터 수명 주기를 포괄적으로 관리 | [![Install](https://img.shields.io/badge/Install-Kiro-9046FF?style=flat-square&logo=kiro)](https://kiro.dev/launch/mcp/add?name=awslabs.healthimaging-mcp-server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.healthimaging-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22AWS_REGION%22%3A%22us-east-1%22%2C%22AWS_PROFILE%22%3A%22your-profile%22%2C%22FASTMCP_LOG_LEVEL%22%3A%22WARNING%22%7D%7D) <br/>[![Install](https://img.shields.io/badge/Install-Cursor-blue?style=flat-square&logo=cursor)](https://cursor.com/en/install-mcp?name=awslabs.healthimaging-mcp-server&config=eyJjb21tYW5kIjoidXZ4IGF3c2xhYnMuaGVhbHRoaW1hZ2luZy1tY3Atc2VydmVyQGxhdGVzdCIsImVudiI6eyJBV1NfUkVHSU9OIjoidXMtZWFzdC0xIiwiQVdTX1BST0ZJTEUiOiJ5b3VyLXByb2ZpbGUiLCJGQVNUTUNQX0xPR19MRVZFTCI6IldBUk5JTkcifX0%3D) <br/>[![Install on VS Code](https://img.shields.io/badge/Install-VS_Code-FF9900?style=flat-square&logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/redirect/mcp/install?name=AWS%20HealthImaging%20MCP%20Server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.healthimaging-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22AWS_REGION%22%3A%22us-east-1%22%2C%22AWS_PROFILE%22%3A%22your-profile%22%2C%22FASTMCP_LOG_LEVEL%22%3A%22WARNING%22%7D%7D) |
| [AWS HealthLake MCP Server](src/healthlake-mcp-server) | 포괄적인 AWS HealthLake 연동으로 FHIR 헬스케어 데이터 워크플로를 생성, 관리, 검색, 최적화합니다. 자동 리소스 검색, 고급 검색 기능, 환자 기록 관리, 원활한 가져오기/내보내기 작업을 제공합니다. | [![Install](https://img.shields.io/badge/Install-Kiro-9046FF?style=flat-square&logo=kiro)](https://kiro.dev/launch/mcp/add?name=awslabs.healthlake-mcp-server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.healthlake-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22AWS_REGION%22%3A%22us-east-1%22%2C%22AWS_PROFILE%22%3A%22your-profile%22%2C%22FASTMCP_LOG_LEVEL%22%3A%22WARNING%22%7D%7D) <br/>[![Install](https://img.shields.io/badge/Install-Cursor-blue?style=flat-square&logo=cursor)](https://cursor.com/en/install-mcp?name=awslabs.healthlake-mcp-server&config=eyJjb21tYW5kIjoidXZ4IGF3c2xhYnMuaGVhbHRobGFrZS1tY3Atc2VydmVyQGxhdGVzdCIsImVudiI6eyJBV1NfUkVHSU9OIjoidXMtZWFzdC0xIiwiQVdTX1BST0ZJTEUiOiJ5b3VyLXByb2ZpbGUiLCJGQVNUTUNQX0xPR19MRVZFTCI6IldBUk5JTkcifX0%3D) <br/>[![Install on VS Code](https://img.shields.io/badge/Install-VS_Code-FF9900?style=flat-square&logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/redirect/mcp/install?name=HealthLake%20MCP%20Server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.healthlake-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22AWS_REGION%22%3A%22us-east-1%22%2C%22AWS_PROFILE%22%3A%22your-profile%22%2C%22FASTMCP_LOG_LEVEL%22%3A%22WARNING%22%7D%7D) |
| [Registry of Open Data (RODA) MCP Server](src/roda-mcp-server) | AWS의 오픈 데이터셋 검색, 탐색, 미리 보기 | [![Install](https://img.shields.io/badge/Install-Kiro-9046FF?style=flat-square&logo=kiro)](https://kiro.dev/launch/mcp/add?name=awslabs.roda-mcp-server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.roda-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%7D%7D) <br/>[![Install](https://img.shields.io/badge/Install-Cursor-blue?style=flat-square&logo=cursor)](https://cursor.com/en/install-mcp?name=awslabs.roda-mcp-server&config=eyJjb21tYW5kIjoidXZ4IGF3c2xhYnMucm9kYS1tY3Atc2VydmVyQGxhdGVzdCIsImVudiI6eyJGQVNUTUNQX0xPR19MRVZFTCI6IkVSUk9SIn0sImRpc2FibGVkIjpmYWxzZSwiYXV0b0FwcHJvdmUiOltdfQ==) <br/>[![Install on VS Code](https://img.shields.io/badge/Install-VS_Code-FF9900?style=flat-square&logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/redirect/mcp/install?name=RODA%20MCP%20Server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.roda-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%7D%2C%22disabled%22%3Afalse%2C%22autoApprove%22%3A%5B%5D%7D) |

---

### 작업 방식별로 살펴보기

#### 👨‍💻 바이브 코딩 및 개발

*Kiro, Cline, Cursor, Claude Code 같은 AI 코딩 어시스턴트로 더 빠르게 개발하기*

**워크샵**: 실습 중심의 안내와 예제는 [Vibe Coding with AWS MCP Servers](https://github.com/aws-solutions-library-samples/guidance-for-vibe-coding-with-aws-mcp-servers) 워크샵을 참고하세요.

##### 핵심 개발 워크플로

| 서버 이름 | 설명 | 설치 |
|-------------|-------------|---------|
| [AWS API MCP Server](src/aws-api-mcp-server) | 일반적인 AWS 상호 작용은 여기서 시작하세요! 명령 검증, 보안 제어, 모든 AWS 서비스 접근을 갖춘 포괄적인 AWS API 지원을 제공합니다. 자연어를 통해 인프라를 관리하고 리소스를 탐색하며 AWS 작업을 실행하는 데 적합합니다. | [![Install](https://img.shields.io/badge/Install-Kiro-9046FF?style=flat-square&logo=kiro)](https://kiro.dev/launch/mcp/add?name=awslabs.aws-api-mcp-server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.aws-api-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22AWS_REGION%22%3A%22us-east-1%22%7D%7D) <br/>[![Install](https://img.shields.io/badge/Install-Cursor-blue?style=flat-square&logo=cursor)](https://cursor.com/en/install-mcp?name=awslabs.aws-api-mcp-server&config=eyJjb21tYW5kIjoidXZ4IGF3c2xhYnMuYXdzLWFwaS1tY3Atc2VydmVyQGxhdGVzdCIsImVudiI6eyJBV1NfUkVHSU9OIjoidXMtZWFzdC0xIn0sImRpc2FibGVkIjpmYWxzZSwiYXV0b0FwcHJvdmUiOltdfQ%3D%3D)<br/>[![Install VS Code](https://img.shields.io/badge/Install-VS_Code-FF9900?style=flat-square&logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/redirect/mcp/install?name=AWS%20API%20MCP%20Server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.aws-api-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22AWS_REGION%22%3A%22us-east-1%22%7D%2C%22type%22%3A%22stdio%22%7D) |
| [AWS Knowledge MCP Server](src/aws-knowledge-mcp-server) | AWS가 호스팅하는 원격 완전 관리형 MCP 서버로, 최신 AWS 문서, API 참조, What's New 게시물, 시작 안내 정보, Builder Center, 블로그 게시물, 아키텍처 참조, Well-Architected 가이드에 대한 접근을 제공합니다. | [![Install](https://img.shields.io/badge/Install-Kiro-9046FF?style=flat-square&logo=kiro)](https://kiro.dev/launch/mcp/add?name=aws-knowledge-mcp&config=%7B%22url%22%3A%22https%3A//knowledge-mcp.global.api.aws%22%7D) <br/>[![Install](https://img.shields.io/badge/Install-Cursor-blue?style=flat-square&logo=cursor)](https://cursor.com/en/install-mcp?name=aws-knowledge-mcp&config=eyJ1cmwiOiJodHRwczovL2tub3dsZWRnZS1tY3AuZ2xvYmFsLmFwaS5hd3MifQ==) <br/>[![Install on VS Code](https://img.shields.io/badge/Install-VS_Code-FF9900?style=flat-square&logo=visualstudiocode&logoColor=white)](https://vscode.dev/redirect/mcp/install?name=aws-knowledge-mcp&config=%7B%22type%22%3A%22http%22%2C%22url%22%3A%22https%3A%2F%2Fknowledge-mcp.global.api.aws%22%7D) |
| [AWS Documentation MCP Server](src/aws-documentation-mcp-server) | 최신 AWS 문서와 API 참조 조회 | [![Install](https://img.shields.io/badge/Install-Kiro-9046FF?style=flat-square&logo=kiro)](https://kiro.dev/launch/mcp/add?name=awslabs.aws-documentation-mcp-server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.aws-documentation-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%2C%22AWS_DOCUMENTATION_PARTITION%22%3A%22aws%22%7D%7D) <br/>[![Install](https://img.shields.io/badge/Install-Cursor-blue?style=flat-square&logo=cursor)](https://cursor.com/en/install-mcp?name=awslabs.aws-documentation-mcp-server&config=eyJjb21tYW5kIjoidXZ4IGF3c2xhYnMuYXdzLWRvY3VtZW50YXRpb24tbWNwLXNlcnZlckBsYXRlc3QiLCJlbnYiOnsiRkFTVE1DUF9MT0dfTEVWRUwiOiJFUlJPUiIsIkFXU19ET0NVTUVOVEFUSU9OX1BBUlRJVElPTiI6ImF3cyJ9LCJkaXNhYmxlZCI6ZmFsc2UsImF1dG9BcHByb3ZlIjpbXX0%3D) <br/>[![Install on VS Code](https://img.shields.io/badge/Install-VS_Code-FF9900?style=flat-square&logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/redirect/mcp/install?name=AWS%20Documentation%20MCP%20Server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.aws-documentation-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%2C%22AWS_DOCUMENTATION_PARTITION%22%3A%22aws%22%7D%2C%22disabled%22%3Afalse%2C%22autoApprove%22%3A%5B%5D%7D) |

##### 코드형 인프라(Infrastructure as Code)

| 서버 이름 | 설명 | 설치 |
|-------------|-------------|---------|
| [AWS IaC MCP Server](src/aws-iac-mcp-server) | CloudFormation 문서 접근, CDK 모범 사례 안내, 컨스트럭트 예제, 보안 검증, 배포 트러블슈팅을 제공하는 완전한 코드형 인프라(IaC) 툴킷 | [![Install](https://img.shields.io/badge/Install-Kiro-9046FF?style=flat-square&logo=kiro)](https://kiro.dev/launch/mcp/add?name=awslabs.aws-iac-mcp-server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.aws-iac-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22AWS_PROFILE%22%3A%22your-aws-profile%22%2C%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%7D%7D) <br/>[![Install](https://img.shields.io/badge/Install-Cursor-blue?style=flat-square&logo=cursor)](https://cursor.com/en/install-mcp?name=awslabs.aws-iac-mcp-server&config=eyJjb21tYW5kIjoidXZ4IGF3c2xhYnMuYXdzLWlhYy1tY3Atc2VydmVyQGxhdGVzdCIsImVudiI6eyJBV1NfUFJPRklMRSI6InlvdXItYXdzLXByb2ZpbGUiLCJGQVNUTUNQX0xPR19MRVZFTCI6IkVSUk9SIn0sImRpc2FibGVkIjpmYWxzZSwiYXV0b0FwcHJvdmUiOltdfQ==IiwiZW52Ijp7IkFXU19QUk9GSUxFIjoieW91ci1hd3MtcHJvZmlsZSIsIkZBU1RNQ1BfTE9HX0xFVkVMIjoiRVJST1IifSwiZGlzYWJsZWQiOmZhbHNlLCJhdXRvQXBwcm92ZSI6W119) <br/>[![Install on VS Code](https://img.shields.io/badge/Install-VS_Code-FF9900?style=flat-square&logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/redirect/mcp/install?name=AWS%20IaC%20MCP%20Server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.aws-iac-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22AWS_PROFILE%22%3A%22your-aws-profile%22%2C%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%7D%2C%22disabled%22%3Afalse%2C%22autoApprove%22%3A%5B%5D%7D) |
| [AWS Cloud Control API MCP Server](src/ccapi-mcp-server) ⚠️ **DEPRECATED** | 보안 스캐닝과 모범 사례를 갖춘 AWS 리소스 직접 관리 ([AWS IaC MCP Server](src/aws-iac-mcp-server)를 대신 사용하세요) | [![Install](https://img.shields.io/badge/Install-Kiro-9046FF?style=flat-square&logo=kiro)](https://kiro.dev/launch/mcp/add?name=awslabs.ccapi-mcp-server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.ccapi-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22AWS_PROFILE%22%3A%22your-aws-profile%22%2C%22AWS_REGION%22%3A%22us-east-1%22%2C%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%7D%7D) <br/>[![Install](https://img.shields.io/badge/Install-Cursor-blue?style=flat-square&logo=cursor)](https://cursor.com/en/install-mcp?name=awslabs.ccapi-mcp-server&config=eyJjb21tYW5kIjoidXZ4IGF3c2xhYnMuY2NhcGktbWNwLXNlcnZlckBsYXRlc3QiLCJlbnYiOnsiQVdTX1BST0ZJTEUiOiJ5b3VyLWF3cy1wcm9maWxlIiwiQVdTX1JFR0lPTiI6InVzLWVhc3QtMSIsIkZBU1RNQ1BfTE9HX0xFVkVMIjoiRVJST1IifSwiZGlzYWJsZWQiOmZhbHNlLCJhdXRvQXBwcm92ZSI6W119) <br/>[![Install on VS Code](https://img.shields.io/badge/Install-VS_Code-FF9900?style=flat-square&logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/redirect/mcp/install?name=AWS%20Cloud%20Control%20API%20MCP%20Server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.ccapi-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22AWS_PROFILE%22%3A%22your-aws-profile%22%2C%22AWS_REGION%22%3A%22us-east-1%22%2C%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%7D%2C%22disabled%22%3Afalse%2C%22autoApprove%22%3A%5B%5D%7D) |

##### 애플리케이션 개발

| 서버 이름 | 설명 | 설치 |
|-------------|-------------|---------|
| [OpenAPI MCP Server](src/openapi-mcp-server) | OpenAPI 명세를 통한 동적 API 통합 | [![Install](https://img.shields.io/badge/Install-Kiro-9046FF?style=flat-square&logo=kiro)](https://kiro.dev/launch/mcp/add?name=awslabs.openapi-mcp-server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.openapi-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22API_NAME%22%3A%22your-api-name%22%2C%22API_BASE_URL%22%3A%22https%3A//api.example.com%22%2C%22API_SPEC_URL%22%3A%22https%3A//api.example.com/openapi.json%22%2C%22LOG_LEVEL%22%3A%22ERROR%22%2C%22ENABLE_PROMETHEUS%22%3A%22false%22%2C%22ENABLE_OPERATION_PROMPTS%22%3A%22true%22%2C%22UVICORN_TIMEOUT_GRACEFUL_SHUTDOWN%22%3A%225.0%22%2C%22UVICORN_GRACEFUL_SHUTDOWN%22%3A%22true%22%7D%7D) <br/>[![Install](https://img.shields.io/badge/Install-Cursor-blue?style=flat-square&logo=cursor)](https://cursor.com/en/install-mcp?name=awslabs.openapi-mcp-server&config=eyJjb21tYW5kIjoidXZ4IGF3c2xhYnMub3BlbmFwaS1tY3Atc2VydmVyQGxhdGVzdCIsImVudiI6eyJBUElfTkFNRSI6InlvdXItYXBpLW5hbWUiLCJBUElfQkFTRV9VUkwiOiJodHRwczovL2FwaS5leGFtcGxlLmNvbSIsIkFQSV9TUEVDX1VSTCI6Imh0dHBzOi8vYXBpLmV4YW1wbGUuY29tL29wZW5hcGkuanNvbiIsIkxPR19MRVZFTCI6IkVSUk9SIiwiRU5BQkxFX1BST01FVEhFVVMiOiJmYWxzZSIsIkVOQUJMRV9PUEVSQVRJT05fUFJPTVBUUyI6InRydWUiLCJVVklDT1JOX1RJTUVPVVRfR1JBQ0VGVUxfU0hVVERPV04iOiI1LjAiLCJVVklDT1JOX0dSQUNFRlVMX1NIVVRET1dOIjoidHJ1ZSJ9LCJkaXNhYmxlZCI6ZmFsc2UsImF1dG9BcHByb3ZlIjpbXX0%3D) <br/>[![Install on VS Code](https://img.shields.io/badge/Install-VS_Code-FF9900?style=flat-square&logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/redirect/mcp/install?name=OpenAPI%20MCP%20Server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.openapi-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22API_NAME%22%3A%22your-api-name%22%2C%22API_BASE_URL%22%3A%22https%3A%2F%2Fapi.example.com%22%2C%22API_SPEC_URL%22%3A%22https%3A%2F%2Fapi.example.com%2Fopenapi.json%22%2C%22LOG_LEVEL%22%3A%22ERROR%22%2C%22ENABLE_PROMETHEUS%22%3A%22false%22%2C%22ENABLE_OPERATION_PROMPTS%22%3A%22true%22%2C%22UVICORN_TIMEOUT_GRACEFUL_SHUTDOWN%22%3A%225.0%22%2C%22UVICORN_GRACEFUL_SHUTDOWN%22%3A%22true%22%7D%2C%22disabled%22%3Afalse%2C%22autoApprove%22%3A%5B%5D%7D) |

##### 컨테이너 및 서버리스 개발

| 서버 이름 | 설명 | 설치 |
|-------------|-------------|---------|
| [Amazon SageMaker AI MCP Server](src/sagemaker-ai-mcp-server) | SageMaker AI 리소스 관리 및 모델 개발 | [![Install](https://img.shields.io/badge/Install-Kiro-9046FF?style=flat-square&logo=kiro)](https://kiro.dev/launch/mcp/add?name=awslabs.sagemaker-ai-mcp-server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.sagemaker-ai-mcp-server%40latest%22%2C%22--allow-write%22%2C%22--allow-sensitive-data-access%22%5D%2C%22env%22%3A%7B%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%7D%7D) <br/>[![Install](https://img.shields.io/badge/Install-Cursor-blue?style=flat-square&logo=cursor)](https://cursor.com/en/install-mcp?name=awslabs.sagemaker-ai-mcp-server&config=eyJhdXRvQXBwcm92ZSI6W10sImRpc2FibGVkIjpmYWxzZSwiY29tbWFuZCI6InV2eCBhd3NsYWJzLnNhZ2VtYWtlci1haS1tY3Atc2VydmVyQGxhdGVzdCAtLWFsbG93LXdyaXRlIC0tYWxsb3ctc2Vuc2l0aXZlLWRhdGEtYWNjZXNzIiwiZW52Ijp7IkZBU1RNQ1BfTE9HX0xFVkVMIjoiRVJST1IifSwidHJhbnNwb3J0VHlwZSI6InN0ZGlvIn0%3D) <br/>[![Install on VS Code](https://img.shields.io/badge/Install-VS_Code-FF9900?style=flat-square&logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/redirect/mcp/install?name=SageMaker%20AI%20MCP%20Server&config=%7B%22autoApprove%22%3A%5B%5D%2C%22disabled%22%3Afalse%2C%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.sagemaker-ai-mcp-server%40latest%22%2C%22--allow-write%22%2C%22--allow-sensitive-data-access%22%5D%2C%22env%22%3A%7B%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%7D%2C%22transportType%22%3A%22stdio%22%7D) |
| [Amazon EKS MCP Server](src/eks-mcp-server) | Kubernetes 클러스터 관리 및 앱 배포 | [![Install](https://img.shields.io/badge/Install-Kiro-9046FF?style=flat-square&logo=kiro)](https://kiro.dev/launch/mcp/add?name=awslabs.eks-mcp-server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.eks-mcp-server%40latest%22%2C%22--allow-write%22%2C%22--allow-sensitive-data-access%22%5D%2C%22env%22%3A%7B%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%7D%7D) <br/>[![Install](https://img.shields.io/badge/Install-Cursor-blue?style=flat-square&logo=cursor)](https://cursor.com/en/install-mcp?name=awslabs.eks-mcp-server&config=eyJhdXRvQXBwcm92ZSI6W10sImRpc2FibGVkIjpmYWxzZSwiY29tbWFuZCI6InV2eCBhd3NsYWJzLmVrcy1tY3Atc2VydmVyQGxhdGVzdCAtLWFsbG93LXdyaXRlIC0tYWxsb3ctc2Vuc2l0aXZlLWRhdGEtYWNjZXNzIiwiZW52Ijp7IkZBU1RNQ1BfTE9HX0xFVkVMIjoiRVJST1IifSwidHJhbnNwb3J0VHlwZSI6InN0ZGlvIn0%3D) <br/>[![Install on VS Code](https://img.shields.io/badge/Install-VS_Code-FF9900?style=flat-square&logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/redirect/mcp/install?name=EKS%20MCP%20Server&config=%7B%22autoApprove%22%3A%5B%5D%2C%22disabled%22%3Afalse%2C%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.eks-mcp-server%40latest%22%2C%22--allow-write%22%2C%22--allow-sensitive-data-access%22%5D%2C%22env%22%3A%7B%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%7D%2C%22transportType%22%3A%22stdio%22%7D) |
| [Amazon ECS MCP Server](src/ecs-mcp-server) | 애플리케이션을 컨테이너화하여 ECS에 배포 | [![Install](https://img.shields.io/badge/Install-Kiro-9046FF?style=flat-square&logo=kiro)](https://kiro.dev/launch/mcp/add?name=awslabs.ecs-mcp-server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22--from%22%2C%22awslabs-ecs-mcp-server%22%2C%22ecs-mcp-server%22%5D%2C%22env%22%3A%7B%22AWS_PROFILE%22%3A%22your-aws-profile%22%2C%22AWS_REGION%22%3A%22your-aws-region%22%2C%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%2C%22FASTMCP_LOG_FILE%22%3A%22/path/to/ecs-mcp-server.log%22%2C%22ALLOW_WRITE%22%3A%22false%22%2C%22ALLOW_SENSITIVE_DATA%22%3A%22false%22%7D%7D) <br/>[![Install](https://img.shields.io/badge/Install-Cursor-blue?style=flat-square&logo=cursor)](https://cursor.com/en/install-mcp?name=awslabs.ecs-mcp-server&config=eyJjb21tYW5kIjoidXZ4IC0tZnJvbSBhd3NsYWJzLWVjcy1tY3Atc2VydmVyIGVjcy1tY3Atc2VydmVyIiwiZW52Ijp7IkFXU19QUk9GSUxFIjoieW91ci1hd3MtcHJvZmlsZSIsIkFXU19SRUdJT04iOiJ5b3VyLWF3cy1yZWdpb24iLCJGQVNUTUNQX0xPR19MRVZFTCI6IkVSUk9SIiwiRkFTVE1DUF9MT0dfRklMRSI6Ii9wYXRoL3RvL2Vjcy1tY3Atc2VydmVyLmxvZyIsIkFMTE9XX1dSSVRFIjoiZmFsc2UiLCJBTExPV19TRU5TSVRJVkVfREFUQSI6ImZhbHNlIn19) <br/>[![Install on VS Code](https://img.shields.io/badge/Install-VS_Code-FF9900?style=flat-square&logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/redirect/mcp/install?name=ECS%20MCP%20Server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22--from%22%2C%22awslabs-ecs-mcp-server%22%2C%22ecs-mcp-server%22%5D%2C%22env%22%3A%7B%22AWS_PROFILE%22%3A%22your-aws-profile%22%2C%22AWS_REGION%22%3A%22your-aws-region%22%2C%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%2C%22FASTMCP_LOG_FILE%22%3A%22%2Fpath%2Fto%2Fecs-mcp-server.log%22%2C%22ALLOW_WRITE%22%3A%22false%22%2C%22ALLOW_SENSITIVE_DATA%22%3A%22false%22%7D%7D) |
| [Finch MCP Server](src/finch-mcp-server) | ECR 푸시를 포함한 로컬 컨테이너 빌드 | [![Install](https://img.shields.io/badge/Install-Kiro-9046FF?style=flat-square&logo=kiro)](https://kiro.dev/launch/mcp/add?name=awslabs.finch-mcp-server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.finch-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22AWS_PROFILE%22%3A%22default%22%2C%22AWS_REGION%22%3A%22us-west-2%22%2C%22FASTMCP_LOG_LEVEL%22%3A%22INFO%22%7D%7D) <br/>[![Install](https://img.shields.io/badge/Install-Cursor-blue?style=flat-square&logo=cursor)](https://cursor.com/en/install-mcp?name=awslabs.finch-mcp-server&config=eyJjb21tYW5kIjoidXZ4IGF3c2xhYnMuZmluY2gtbWNwLXNlcnZlckBsYXRlc3QiLCJlbnYiOnsiQVdTX1BST0ZJTEUiOiJkZWZhdWx0IiwiQVdTX1JFR0lPTiI6InVzLXdlc3QtMiIsIkZBU1RNQ1BfTE9HX0xFVkVMIjoiSU5GTyJ9LCJ0cmFuc3BvcnRUeXBlIjoic3RkaW8iLCJkaXNhYmxlZCI6ZmFsc2UsImF1dG9BcHByb3ZlIjpbXX0%3D) <br/>[![Install on VS Code](https://img.shields.io/badge/Install-VS_Code-FF9900?style=flat-square&logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/redirect/mcp/install?name=Finch%20MCP%20Server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.finch-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22AWS_PROFILE%22%3A%22default%22%2C%22AWS_REGION%22%3A%22us-west-2%22%2C%22FASTMCP_LOG_LEVEL%22%3A%22INFO%22%7D%2C%22transportType%22%3A%22stdio%22%2C%22disabled%22%3Afalse%2C%22autoApprove%22%3A%5B%5D%7D) |
| [AWS Serverless MCP Server](src/aws-serverless-mcp-server) | SAM CLI를 활용한 서버리스 앱 전체 수명 주기 관리 | [![Install](https://img.shields.io/badge/Install-Kiro-9046FF?style=flat-square&logo=kiro)](https://kiro.dev/launch/mcp/add?name=awslabs.aws-serverless-mcp-server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.aws-serverless-mcp-server%40latest%22%2C%22--allow-write%22%2C%22--allow-sensitive-data-access%22%5D%2C%22env%22%3A%7B%22AWS_PROFILE%22%3A%22your-aws-profile%22%2C%22AWS_REGION%22%3A%22us-east-1%22%7D%7D) <br/>[![Install](https://img.shields.io/badge/Install-Cursor-blue?style=flat-square&logo=cursor)](https://cursor.com/en/install-mcp?name=awslabs.aws-serverless-mcp-server&config=eyJjb21tYW5kIjoidXZ4IGF3c2xhYnMuYXdzLXNlcnZlcmxlc3MtbWNwLXNlcnZlckBsYXRlc3QgLS1hbGxvdy13cml0ZSAtLWFsbG93LXNlbnNpdGl2ZS1kYXRhLWFjY2VzcyIsImVudiI6eyJBV1NfUFJPRklMRSI6InlvdXItYXdzLXByb2ZpbGUiLCJBV1NfUkVHSU9OIjoidXMtZWFzdC0xIn0sImRpc2FibGVkIjpmYWxzZSwiYXV0b0FwcHJvdmUiOltdfQ%3D%3D) <br/>[![Install on VS Code](https://img.shields.io/badge/Install-VS_Code-FF9900?style=flat-square&logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/redirect/mcp/install?name=AWS%20Serverless%20MCP%20Server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.aws-serverless-mcp-server%40latest%22%2C%22--allow-write%22%2C%22--allow-sensitive-data-access%22%5D%2C%22env%22%3A%7B%22AWS_PROFILE%22%3A%22your-aws-profile%22%2C%22AWS_REGION%22%3A%22us-east-1%22%7D%2C%22disabled%22%3Afalse%2C%22autoApprove%22%3A%5B%5D%7D) |


##### 테스트 및 데이터

| 서버 이름 | 설명 | 설치 |
|-------------|-------------|---------|

##### 생명과학 워크플로 개발

| 서버 이름 | 설명 | 설치 |
|-------------|-------------|---------|
| [AWS HealthOmics MCP Server](src/aws-healthomics-mcp-server) | 생명과학 워크플로 생성, 실행, 디버깅, 최적화 | [![Install](https://img.shields.io/badge/Install-Kiro-9046FF?style=flat-square&logo=kiro)](https://kiro.dev/launch/mcp/add?name=awslabs.aws-healthomics-mcp-server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.aws-healthomics-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22AWS_REGION%22%3A%22us-east-1%22%2C%22AWS_PROFILE%22%3A%22your-profile%22%2C%22FASTMCP_LOG_LEVEL%22%3A%22WARNING%22%7D%7D) <br/>[![Install](https://img.shields.io/badge/Install-Cursor-blue?style=flat-square&logo=cursor)](https://cursor.com/en/install-mcp?name=awslabs.aws-healthomics-mcp-server&config=eyJjb21tYW5kIjoidXZ4IGF3c2xhYnMuYXdzLWhlYWx0aG9taWNzLW1jcC1zZXJ2ZXJAbGF0ZXN0IiwiZW52Ijp7IkFXU19SRUdJT04iOiJ1cy1lYXN0LTEiLCJBV1NfUFJPRklMRSI6InlvdXItcHJvZmlsZSIsIkZBU1RNQ1BfTE9HX0xFVkVMIjoiV0FSTklORyJ9fQ%3D%3D) <br/>[![Install on VS Code](https://img.shields.io/badge/Install-VS_Code-FF9900?style=flat-square&logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/redirect/mcp/install?name=AWS%20HealthOmics%20MCP%20Server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.aws-healthomics-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22AWS_REGION%22%3A%22us-east-1%22%2C%22AWS_PROFILE%22%3A%22your-profile%22%2C%22FASTMCP_LOG_LEVEL%22%3A%22WARNING%22%7D%7D) |

##### 헬스케어 데이터 관리

| 서버 이름 | 설명 | 설치 |
|-------------|-------------|---------|
| [AWS HealthLake MCP Server](src/healthlake-mcp-server) | 포괄적인 AWS HealthLake 연동으로 FHIR 헬스케어 데이터 워크플로를 생성, 관리, 검색, 최적화합니다. 자동 리소스 검색, 고급 검색 기능, 환자 기록 관리, 원활한 가져오기/내보내기 작업을 제공합니다. | [![Install](https://img.shields.io/badge/Install-Kiro-9046FF?style=flat-square&logo=kiro)](https://kiro.dev/launch/mcp/add?name=awslabs.healthlake-mcp-server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.healthlake-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22AWS_REGION%22%3A%22us-east-1%22%2C%22AWS_PROFILE%22%3A%22your-profile%22%2C%22FASTMCP_LOG_LEVEL%22%3A%22WARNING%22%7D%7D) <br/>[![Install](https://img.shields.io/badge/Install-Cursor-blue?style=flat-square&logo=cursor)](https://cursor.com/en/install-mcp?name=awslabs.healthlake-mcp-server&config=eyJjb21tYW5kIjoidXZ4IGF3c2xhYnMuaGVhbHRobGFrZS1tY3Atc2VydmVyQGxhdGVzdCIsImVudiI6eyJBV1NfUkVHSU9OIjoidXMtZWFzdC0xIiwiQVdTX1BST0ZJTEUiOiJ5b3VyLXByb2ZpbGUiLCJGQVNUTUNQX0xPR19MRVZFTCI6IldBUk5JTkcifX0%3D) <br/>[![Install on VS Code](https://img.shields.io/badge/Install-VS_Code-FF9900?style=flat-square&logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/redirect/mcp/install?name=HealthLake%20MCP%20Server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.healthlake-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22AWS_REGION%22%3A%22us-east-1%22%2C%22AWS_PROFILE%22%3A%22your-profile%22%2C%22FASTMCP_LOG_LEVEL%22%3A%22WARNING%22%7D%7D) |


#### 💬 대화형 어시스턴트

*고객 대면 챗봇, 비즈니스 에이전트, 대화형 Q&A 시스템*

##### 지식 및 검색

| 서버 이름 | 설명 | 설치 |
|-------------|-------------|---------|
| [Amazon Bedrock Knowledge Bases Retrieval MCP Server](src/bedrock-kb-retrieval-mcp-server) | 인용 정보를 포함한 엔터프라이즈 기술 자료 조회 | [![Install](https://img.shields.io/badge/Install-Kiro-9046FF?style=flat-square&logo=kiro)](https://kiro.dev/launch/mcp/add?name=awslabs.bedrock-kb-retrieval-mcp-server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.bedrock-kb-retrieval-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22AWS_PROFILE%22%3A%22your-profile-name%22%2C%22AWS_REGION%22%3A%22us-east-1%22%2C%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%2C%22KB_INCLUSION_TAG_KEY%22%3A%22optional-tag-key-to-filter-kbs%22%2C%22BEDROCK_KB_RERANKING_ENABLED%22%3A%22false%22%7D%7D) <br/>[![Install](https://img.shields.io/badge/Install-Cursor-blue?style=flat-square&logo=cursor)](https://cursor.com/en/install-mcp?name=awslabs.bedrock-kb-retrieval-mcp-server&config=eyJjb21tYW5kIjoidXZ4IGF3c2xhYnMuYmVkcm9jay1rYi1yZXRyaWV2YWwtbWNwLXNlcnZlckBsYXRlc3QiLCJlbnYiOnsiQVdTX1BST0ZJTEUiOiJ5b3VyLXByb2ZpbGUtbmFtZSIsIkFXU19SRUdJT04iOiJ1cy1lYXN0LTEiLCJGQVNUTUNQX0xPR19MRVZFTCI6IkVSUk9SIiwiS0JfSU5DTFVTSU9OX1RBR19LRVkiOiJvcHRpb25hbC10YWcta2V5LXRvLWZpbHRlci1rYnMiLCJCRURST0NLX0tCX1JFUkFOS0lOR19FTkFCTEVEIjoiZmFsc2UifSwiZGlzYWJsZWQiOmZhbHNlLCJhdXRvQXBwcm92ZSI6W119) <br/>[![Install on VS Code](https://img.shields.io/badge/Install-VS_Code-FF9900?style=flat-square&logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/redirect/mcp/install?name=Bedrock%20KB%20Retrieval%20MCP%20Server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.bedrock-kb-retrieval-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22AWS_PROFILE%22%3A%22your-profile-name%22%2C%22AWS_REGION%22%3A%22us-east-1%22%2C%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%2C%22KB_INCLUSION_TAG_KEY%22%3A%22optional-tag-key-to-filter-kbs%22%2C%22BEDROCK_KB_RERANKING_ENABLED%22%3A%22false%22%7D%2C%22disabled%22%3Afalse%2C%22autoApprove%22%3A%5B%5D%7D) |
| [Amazon Kendra Index MCP Server](src/amazon-kendra-index-mcp-server) | 엔터프라이즈 검색 및 RAG 강화 | [![Install](https://img.shields.io/badge/Install-Kiro-9046FF?style=flat-square&logo=kiro)](https://kiro.dev/launch/mcp/add?name=awslabs.amazon-kendra-index-mcp-server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.amazon-kendra-index-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22AWS_REGION%22%3A%22us-east-1%22%2C%22KEND_INDEX_ID%22%3A%22your-kendra-index-id%22%2C%22KEND_ROLE_ARN%22%3A%22your-kendra-role-arn%22%2C%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%7D%7D) <br/>[![Install](https://img.shields.io/badge/Install-Cursor-blue?style=flat-square&logo=cursor)](https://cursor.com/en/install-mcp?name=awslabs.amazon-kendra-index-mcp-server&config=eyJjb21tYW5kIjoidXZ4IGF3c2xhYnMuYW1hem9uLWtlbmRyYS1pbmRleC1tY3Atc2VydmVyQGxhdGVzdCIsImVudiI6eyJBV1NfUkVHSU9OIjoidXMtZWFzdC0xIiwiS0VORF9JTkRFWF9JRCI6InlvdXIta2VuZHJhLWluZGV4LWlkIiwiS0VORF9ST0xFX0FSTiI6InlvdXIta2VuZHJhLXJvbGUtYXJuIiwiRkFTVE1DUF9MT0dfTEVWRUwiOiJFUlJPUiJ9LCJkaXNhYmxlZCI6ZmFsc2UsImF1dG9BcHByb3ZlIjpbXX0%3D) <br/>[![Install on VS Code](https://img.shields.io/badge/Install-VS_Code-FF9900?style=flat-square&logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/redirect/mcp/install?name=Amazon%20Kendra%20Index%20MCP%20Server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.amazon-kendra-index-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22AWS_REGION%22%3A%22us-east-1%22%2C%22KEND_INDEX_ID%22%3A%22your-kendra-index-id%22%2C%22KEND_ROLE_ARN%22%3A%22your-kendra-role-arn%22%2C%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%7D%2C%22disabled%22%3Afalse%2C%22autoApprove%22%3A%5B%5D%7D) |
| [Amazon Q Business MCP Server](src/amazon-qbusiness-anonymous-mcp-server) | 익명 접근을 지원하는, 수집된 콘텐츠 기반 AI 어시스턴트 | [![Install](https://img.shields.io/badge/Install-Kiro-9046FF?style=flat-square&logo=kiro)](https://kiro.dev/launch/mcp/add?name=awslabs.amazon-qbusiness-anonymous-mcp-server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.amazon-qbusiness-anonymous-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22QBUSINESS_APP_ID%22%3A%22your-qbusiness-app-id%22%2C%22QBUSINESS_USER_ID%22%3A%22your-user-id%22%2C%22AWS_PROFILE%22%3A%22your-aws-profile%22%2C%22AWS_REGION%22%3A%22us-east-1%22%2C%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%7D%7D) <br/>[![Install](https://img.shields.io/badge/Install-Cursor-blue?style=flat-square&logo=cursor)](https://cursor.com/en/install-mcp?name=awslabs.amazon-qbusiness-anonymous-mcp-server&config=eyJjb21tYW5kIjoidXZ4IGF3c2xhYnMuYW1hem9uLXFidXNpbmVzcy1hbm9ueW1vdXMtbWNwLXNlcnZlckBsYXRlc3QiLCJlbnYiOnsiUUJVU0lORVNTX0FQUF9JRCI6InlvdXItcWJ1c2luZXNzLWFwcC1pZCIsIlFCVVNJTkVTU19VU0VSX0lEIjoieW91ci11c2VyLWlkIiwiQVdTX1BST0ZJTEUiOiJ5b3VyLWF3cy1wcm9maWxlIiwiQVdTX1JFR0lPTiI6InVzLWVhc3QtMSIsIkZBU1RNQ1BfTE9HX0xFVkVMIjoiRVJST1IifSwiZGlzYWJsZWQiOmZhbHNlLCJhdXRvQXBwcm92ZSI6W119) <br/>[![Install on VS Code](https://img.shields.io/badge/Install-VS_Code-FF9900?style=flat-square&logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/redirect/mcp/install?name=Amazon%20Q%20Business%20Anonymous%20MCP%20Server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.amazon-qbusiness-anonymous-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22QBUSINESS_APP_ID%22%3A%22your-qbusiness-app-id%22%2C%22QBUSINESS_USER_ID%22%3A%22your-user-id%22%2C%22AWS_PROFILE%22%3A%22your-aws-profile%22%2C%22AWS_REGION%22%3A%22us-east-1%22%2C%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%7D%2C%22disabled%22%3Afalse%2C%22autoApprove%22%3A%5B%5D%7D) |
| [Amazon Q Index MCP Server](src/amazon-qindex-mcp-server) | 엔터프라이즈 Q 인덱스를 검색하는 데이터 액세서 | [![Install](https://img.shields.io/badge/Install-Kiro-9046FF?style=flat-square&logo=kiro)](https://kiro.dev/launch/mcp/add?name=awslabs.amazon-qindex-mcp-server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.amazon-qindex-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22AWS_REGION%22%3A%22us-east-1%22%2C%22QINDEX_ID%22%3A%22your-qindex-id%22%2C%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%7D%7D) <br/>[![Install](https://img.shields.io/badge/Install-Cursor-blue?style=flat-square&logo=cursor)](https://cursor.com/en/install-mcp?name=awslabs.amazon-qindex-mcp-server&config=eyJjb21tYW5kIjoidXZ4IGF3c2xhYnMuYW1hem9uLXFpbmRleC1tY3Atc2VydmVyQGxhdGVzdCIsImVudiI6eyJBV1NfUkVHSU9OIjoidXMtZWFzdC0xIiwiUUlOREVYX0lEIjoieW91ci1xaW5kZXgtaWQiLCJGQVNUTUNQX0xPR19MRVZFTCI6IkVSUk9SIn0sImRpc2FibGVkIjpmYWxzZSwiYXV0b0FwcHJvdmUiOltdfQ%3D%3D) <br/>[![Install on VS Code](https://img.shields.io/badge/Install-VS_Code-FF9900?style=flat-square&logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/redirect/mcp/install?name=Amazon%20Q%20Index%20MCP%20Server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.amazon-qindex-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22AWS_REGION%22%3A%22us-east-1%22%2C%22QINDEX_ID%22%3A%22your-qindex-id%22%2C%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%7D%2C%22disabled%22%3Afalse%2C%22autoApprove%22%3A%5B%5D%7D) |
| [AWS Documentation MCP Server](src/aws-documentation-mcp-server) | 최신 AWS 문서와 API 참조 조회 | [![Install](https://img.shields.io/badge/Install-Kiro-9046FF?style=flat-square&logo=kiro)](https://kiro.dev/launch/mcp/add?name=awslabs.aws-documentation-mcp-server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.aws-documentation-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%2C%22AWS_DOCUMENTATION_PARTITION%22%3A%22aws%22%7D%7D) <br/>[![Install](https://img.shields.io/badge/Install-Cursor-blue?style=flat-square&logo=cursor)](https://cursor.com/en/install-mcp?name=awslabs.aws-documentation-mcp-server&config=eyJjb21tYW5kIjoidXZ4IGF3c2xhYnMuYXdzLWRvY3VtZW50YXRpb24tbWNwLXNlcnZlckBsYXRlc3QiLCJlbnYiOnsiRkFTVE1DUF9MT0dfTEVWRUwiOiJFUlJPUiIsIkFXU19ET0NVTUVOVEFUSU9OX1BBUlRJVElPTiI6ImF3cyJ9LCJkaXNhYmxlZCI6ZmFsc2UsImF1dG9BcHByb3ZlIjpbXX0%3D) <br/>[![Install on VS Code](https://img.shields.io/badge/Install-VS_Code-FF9900?style=flat-square&logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/redirect/mcp/install?name=AWS%20Documentation%20MCP%20Server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.aws-documentation-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%2C%22AWS_DOCUMENTATION_PARTITION%22%3A%22aws%22%7D%2C%22disabled%22%3Afalse%2C%22autoApprove%22%3A%5B%5D%7D) |

##### 콘텐츠 처리 및 생성

| 서버 이름 | 설명 | 설치 |
|-------------|-------------|---------|
| [Document Loader MCP Server](src/document-loader-mcp-server) | PDF, DOCX, XLSX, PPTX 및 이미지 파일의 콘텐츠 파싱 및 추출 | [![Install](https://img.shields.io/badge/Install-Kiro-9046FF?style=flat-square&logo=kiro)](https://kiro.dev/launch/mcp/add?name=awslabs.document-loader-mcp-server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.document-loader-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%7D%7D) <br/>[![Install](https://img.shields.io/badge/Install-Cursor-blue?style=flat-square&logo=cursor)](https://cursor.com/en/install-mcp?name=awslabs.document-loader-mcp-server&config=eyJjb21tYW5kIjoidXZ4IiwiYXJncyI6WyJhd3NsYWJzLmRvY3VtZW50LWxvYWRlci1tY3Atc2VydmVyQGxhdGVzdCJdLCJlbnYiOnsiRkFTVE1DUF9MT0dfTEVWRUwiOiJFUlJPUiJ9LCJkaXNhYmxlZCI6ZmFsc2UsImF1dG9BcHByb3ZlIjpbXX0%3D) <br/>[![Install on VS Code](https://img.shields.io/badge/Install-VS_Code-FF9900?style=flat-square&logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/redirect/mcp/install?name=Document%20Loader%20MCP%20Server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.document-loader-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%7D%2C%22disabled%22%3Afalse%2C%22autoApprove%22%3A%5B%5D%7D) |
| [Amazon Translate MCP Server](src/amazon-translate-mcp-server) | 배치 처리와 사용자 지정 용어집을 지원하는 75개 이상 언어의 신경망 기계 번역 | [![Install](https://img.shields.io/badge/Install-Kiro-9046FF?style=flat-square&logo=kiro)](https://kiro.dev/launch/mcp/add?name=awslabs.amazon-translate-mcp-server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.amazon-translate-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22AWS_PROFILE%22%3A%22your-aws-profile%22%2C%22AWS_REGION%22%3A%22us-east-1%22%2C%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%7D%7D) <br/>[![Install](https://img.shields.io/badge/Install-Cursor-blue?style=flat-square&logo=cursor)](https://cursor.com/en/install-mcp?name=awslabs.amazon-translate-mcp-server&config=eyJjb21tYW5kIjoidXZ4IGF3c2xhYnMuYW1hem9uLXRyYW5zbGF0ZS1tY3Atc2VydmVyQGxhdGVzdCIsImVudiI6eyJBV1NfUFJPRklMRSI6InlvdXItYXdzLXByb2ZpbGUiLCJBV1NfUkVHSU9OIjoidXMtZWFzdC0xIiwiRkFTVE1DUF9MT0dfTEVWRUwiOiJFUlJPUiJ9LCJkaXNhYmxlZCI6ZmFsc2UsImF1dG9BcHByb3ZlIjpbXX0%3D) <br/>[![Install on VS Code](https://img.shields.io/badge/Install-VS_Code-FF9900?style=flat-square&logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/redirect/mcp/install?name=Amazon%20Translate%20MCP%20Server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.amazon-translate-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22AWS_PROFILE%22%3A%22your-aws-profile%22%2C%22AWS_REGION%22%3A%22us-east-1%22%2C%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%7D%2C%22disabled%22%3Afalse%2C%22autoApprove%22%3A%5B%5D%7D) |

##### 비즈니스 서비스

| 서버 이름 | 설명 | 설치 |
|-------------|-------------|---------|
| [Amazon Location Service MCP Server](src/aws-location-mcp-server) | 위치 검색, 지오코딩, 영업시간 조회 | [![Install](https://img.shields.io/badge/Install-Kiro-9046FF?style=flat-square&logo=kiro)](https://kiro.dev/launch/mcp/add?name=awslabs.aws-location-mcp-server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.aws-location-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22AWS_PROFILE%22%3A%22your-aws-profile%22%2C%22AWS_REGION%22%3A%22us-east-1%22%2C%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%7D%7D) <br/>[![Install](https://img.shields.io/badge/Install-Cursor-blue?style=flat-square&logo=cursor)](https://cursor.com/en/install-mcp?name=awslabs.aws-location-mcp-server&config=eyJjb21tYW5kIjoidXZ4IGF3c2xhYnMuYXdzLWxvY2F0aW9uLW1jcC1zZXJ2ZXJAbGF0ZXN0IiwiZW52Ijp7IkFXU19QUk9GSUxFIjoieW91ci1hd3MtcHJvZmlsZSIsIkFXU19SRUdJT04iOiJ1cy1lYXN0LTEiLCJGQVNUTUNQX0xPR19MRVZFTCI6IkVSUk9SIn0sImRpc2FibGVkIjpmYWxzZSwiYXV0b0FwcHJvdmUiOltdfQ%3D%3D) <br/>[![Install on VS Code](https://img.shields.io/badge/Install-VS_Code-FF9900?style=flat-square&logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/redirect/mcp/install?name=AWS%20Location%20MCP%20Server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.aws-location-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22AWS_PROFILE%22%3A%22your-aws-profile%22%2C%22AWS_REGION%22%3A%22us-east-1%22%2C%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%7D%2C%22disabled%22%3Afalse%2C%22autoApprove%22%3A%5B%5D%7D) |
| [AWS Pricing MCP Server](src/aws-pricing-mcp-server) | AWS 서비스 요금 조회 및 비용 추정 | [![Install](https://img.shields.io/badge/Install-Kiro-9046FF?style=flat-square&logo=kiro)](https://kiro.dev/launch/mcp/add?name=awslabs.aws-pricing-mcp-server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.aws-pricing-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%2C%22AWS_PROFILE%22%3A%22your-aws-profile%22%2C%22AWS_REGION%22%3A%22us-east-1%22%7D%7D) <br/>[![Install](https://img.shields.io/badge/Install-Cursor-blue?style=flat-square&logo=cursor)](https://cursor.com/en/install-mcp?name=awslabs.aws-pricing-mcp-server&config=ewogICAgImNvbW1hbmQiOiAidXZ4IGF3c2xhYnMuYXdzLXByaWNpbmctbWNwLXNlcnZlckBsYXRlc3QiLAogICAgImVudiI6IHsKICAgICAgIkZBU1RNQ1BfTE9HX0xFVkVMIjogIkVSUk9SIiwKICAgICAgIkFXU19QUk9GSUxFIjogInlvdXItYXdzLXByb2ZpbGUiLAogICAgICAiQVdTX1JFR0lPTiI6ICJ1cy1lYXN0LTEiCiAgICB9LAogICAgImRpc2FibGVkIjogZmFsc2UsCiAgICAiYXV0b0FwcHJvdmUiOiBbXQogIH0K) <br/>[![Install on VS Code](https://img.shields.io/badge/Install-VS_Code-FF9900?style=flat-square&logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/redirect/mcp/install?name=AWS%20Pricing%20MCP%20Server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.aws-pricing-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%2C%22AWS_PROFILE%22%3A%22your-aws-profile%22%2C%22AWS_REGION%22%3A%22us-east-1%22%7D%2C%22disabled%22%3Afalse%2C%22autoApprove%22%3A%5B%5D%7D) |

#### 🤖 자율 백그라운드 에이전트

*헤드리스 자동화, ETL 파이프라인, 운영 시스템*

##### 데이터 운영 및 ETL

| 서버 이름 | 설명 | 설치 |
|-------------|-------------|---------|
| [AWS Data Processing MCP Server](src/aws-dataprocessing-mcp-server) | AWS Glue, Amazon EMR-EC2, Amazon Athena 전반의 포괄적인 데이터 처리 도구 및 실시간 파이프라인 가시성 | [![Install](https://img.shields.io/badge/Install-Kiro-9046FF?style=flat-square&logo=kiro)](https://kiro.dev/launch/mcp/add?name=awslabs.aws-dataprocessing-mcp-server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.aws-dataprocessing-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22AWS_PROFILE%22%3A%22your-aws-profile%22%2C%22AWS_REGION%22%3A%22us-east-1%22%2C%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%7D%7D) <br/>[![Install](https://img.shields.io/badge/Install-Cursor-blue?style=flat-square&logo=cursor)](https://cursor.com/en/install-mcp?name=awslabs.aws-dataprocessing-mcp-server&config=eyJjb21tYW5kIjoidXZ4IGF3c2xhYnMuYXdzLWRhdGFwcm9jZXNzaW5nLW1jcC1zZXJ2ZXJAbGF0ZXN0IiwiZW52Ijp7IkFXU19QUk9GSUxFIjoieW91ci1hd3MtcHJvZmlsZSIsIkFXU19SRUdJT04iOiJ1cy1lYXN0LTEiLCJGQVNUTUNQX0xPR19MRVZFTCI6IkVSUk9SIn0sImRpc2FibGVkIjpmYWxzZSwiYXV0b0FwcHJvdmUiOltdfQ%3D%3D) <br/>[![Install on VS Code](https://img.shields.io/badge/Install-VS_Code-FF9900?style=flat-square&logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/redirect/mcp/install?name=AWS%20Data%20Processing%20MCP%20Server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.aws-dataprocessing-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22AWS_PROFILE%22%3A%22your-aws-profile%22%2C%22AWS_REGION%22%3A%22us-east-1%22%2C%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%7D%2C%22disabled%22%3Afalse%2C%22autoApprove%22%3A%5B%5D%7D) |
| [Amazon DynamoDB MCP Server](src/dynamodb-mcp-server) | DynamoDB 전체 작업 및 테이블 관리 | [![Install](https://img.shields.io/badge/Install-Kiro-9046FF?style=flat-square&logo=kiro)](https://kiro.dev/launch/mcp/add?name=awslabs-dynamodb-mcp-server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.dynamodb-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22DDB-MCP-READONLY%22%3A%22true%22%2C%22AWS_PROFILE%22%3A%22default%22%2C%22AWS_REGION%22%3A%22us-west-2%22%2C%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%7D%7D) <br/>[![Install](https://img.shields.io/badge/Install-Cursor-blue?style=flat-square&logo=cursor)](https://cursor.com/en/install-mcp?name=awslabs-dynamodb-mcp-server&config=eyJjb21tYW5kIjoidXZ4IGF3c2xhYnMuZHluYW1vZGItbWNwLXNlcnZlckBsYXRlc3QiLCJlbnYiOnsiRERCLU1DUC1SRUFET05MWSI6InRydWUiLCJBV1NfUFJPRklMRSI6ImRlZmF1bHQiLCJBV1NfUkVHSU9OIjoidXMtd2VzdC0yIiwiRkFTVE1DUF9MT0dfTEVWRUwiOiJFUlJPUiJ9LCJkaXNhYmxlZCI6ZmFsc2UsImF1dG9BcHByb3ZlIjpbXX0%3D) <br/>[![Install on VS Code](https://img.shields.io/badge/Install-VS_Code-FF9900?style=flat-square&logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/redirect/mcp/install?name=DynamoDB%20MCP%20Server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.dynamodb-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22DDB-MCP-READONLY%22%3A%22true%22%2C%22AWS_PROFILE%22%3A%22default%22%2C%22AWS_REGION%22%3A%22us-west-2%22%2C%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%7D%2C%22disabled%22%3Afalse%2C%22autoApprove%22%3A%5B%5D%7D) |
| [Amazon Aurora PostgreSQL MCP Server](src/postgres-mcp-server) | RDS Data API를 통한 PostgreSQL 데이터베이스 작업 | [![Install](https://img.shields.io/badge/Install-Kiro-9046FF?style=flat-square&logo=kiro)](https://kiro.dev/launch/mcp/add?name=awslabs.postgres-mcp-server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.postgres-mcp-server%40latest%22%2C%22--connection-string%22%2C%22postgresql%3A//%5Busername%5D%3A%5Bpassword%5D%40%5Bhost%5D%3A%5Bport%5D/%5Bdatabase%5D%22%5D%2C%22env%22%3A%7B%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%7D%7D) <br/>[![Install](https://img.shields.io/badge/Install-Cursor-blue?style=flat-square&logo=cursor)](https://cursor.com/en/install-mcp?name=awslabs.postgres-mcp-server&config=eyJjb21tYW5kIjoidXZ4IGF3c2xhYnMucG9zdGdyZXMtbWNwLXNlcnZlckBsYXRlc3QgLS1jb25uZWN0aW9uLXN0cmluZyBwb3N0Z3Jlc3FsOi8vW3VzZXJuYW1lXTpbcGFzc3dvcmRdQFtob3N0XTpbcG9ydF0vW2RhdGFiYXNlXSIsImVudiI6eyJGQVNUTUNQX0xPR19MRVZFTCI6IkVSUk9SIn0sImRpc2FibGVkIjpmYWxzZSwiYXV0b0FwcHJvdmUiOltdLCJ0cmFuc3BvcnRUeXBlIjoic3RkaW8iLCJhdXRvU3RhcnQiOnRydWV9) <br/>[![Install on VS Code](https://img.shields.io/badge/Install-VS_Code-FF9900?style=flat-square&logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/redirect/mcp/install?name=PostgreSQL%20MCP%20Server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.postgres-mcp-server%40latest%22%2C%22--connection-string%22%2C%22postgresql%3A%2F%2F%5Busername%5D%3A%5Bpassword%5D%40%5Bhost%5D%3A%5Bport%5D%2F%5Bdatabase%5D%22%5D%2C%22env%22%3A%7B%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%7D%2C%22disabled%22%3Afalse%2C%22autoApprove%22%3A%5B%5D%2C%22transportType%22%3A%22stdio%22%2C%22autoStart%22%3Atrue%7D) |
| [Amazon Aurora MySQL MCP Server](src/mysql-mcp-server) | RDS Data API를 통한 MySQL 데이터베이스 작업 | [![Install](https://img.shields.io/badge/Install-Kiro-9046FF?style=flat-square&logo=kiro)](https://kiro.dev/launch/mcp/add?name=awslabs.mysql-mcp-server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.mysql-mcp-server%40latest%22%2C%22--resource_arn%22%2C%22%5Byour%22%2C%22data%5D%22%2C%22--secret_arn%22%2C%22%5Byour%22%2C%22data%5D%22%2C%22--database%22%2C%22%5Byour%22%2C%22data%5D%22%2C%22--region%22%2C%22%5Byour%22%2C%22data%5D%22%2C%22--readonly%22%2C%22True%22%5D%2C%22env%22%3A%7B%22AWS_PROFILE%22%3A%22your-aws-profile%22%2C%22AWS_REGION%22%3A%22us-east-1%22%2C%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%7D%7D) <br/>[![Install](https://img.shields.io/badge/Install-Cursor-blue?style=flat-square&logo=cursor)](https://cursor.com/en/install-mcp?name=awslabs.mysql-mcp-server&config=eyJjb21tYW5kIjoidXZ4IGF3c2xhYnMubXlzcWwtbWNwLXNlcnZlckBsYXRlc3QgLS1yZXNvdXJjZV9hcm4gW3lvdXIgZGF0YV0gLS1zZWNyZXRfYXJuIFt5b3VyIGRhdGFdIC0tZGF0YWJhc2UgW3lvdXIgZGF0YV0gLS1yZWdpb24gW3lvdXIgZGF0YV0gLS1yZWFkb25seSBUcnVlIiwiZW52Ijp7IkFXU19QUk9GSUxFIjoieW91ci1hd3MtcHJvZmlsZSIsIkFXU19SRUdJT04iOiJ1cy1lYXN0LTEiLCJGQVNUTUNQX0xPR19MRVZFTCI6IkVSUk9SIn0sImRpc2FibGVkIjpmYWxzZSwiYXV0b0FwcHJvdmUiOltdfQ%3D%3D) <br/>[![Install on VS Code](https://img.shields.io/badge/Install-VS_Code-FF9900?style=flat-square&logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/redirect/mcp/install?name=MySQL%20MCP%20Server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.mysql-mcp-server%40latest%22%2C%22--resource_arn%22%2C%22%5Byour%20data%5D%22%2C%22--secret_arn%22%2C%22%5Byour%20data%5D%22%2C%22--database%22%2C%22%5Byour%20data%5D%22%2C%22--region%22%2C%22%5Byour%20data%5D%22%2C%22--readonly%22%2C%22True%22%5D%2C%22env%22%3A%7B%22AWS_PROFILE%22%3A%22your-aws-profile%22%2C%22AWS_REGION%22%3A%22us-east-1%22%2C%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%7D%2C%22disabled%22%3Afalse%2C%22autoApprove%22%3A%5B%5D%7D) |
| [Amazon Aurora DSQL MCP Server](src/aurora-dsql-mcp-server) | PostgreSQL 호환 분산 SQL | [![Install](https://img.shields.io/badge/Install-Kiro-9046FF?style=flat-square&logo=kiro)](https://kiro.dev/launch/mcp/add?name=awslabs.aurora-dsql-mcp-server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.aurora-dsql-mcp-server%40latest%22%2C%22--cluster_endpoint%22%2C%22%5Byour%22%2C%22dsql%22%2C%22cluster%22%2C%22endpoint%5D%22%2C%22--region%22%2C%22%5Byour%22%2C%22dsql%22%2C%22cluster%22%2C%22region%2C%22%2C%22e.g.%22%2C%22us-east-1%5D%22%2C%22--database_user%22%2C%22%5Byour%22%2C%22dsql%22%2C%22username%5D%22%2C%22--profile%22%2C%22default%22%5D%2C%22env%22%3A%7B%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%7D%7D) <br/>[![Install](https://img.shields.io/badge/Install-Cursor-blue?style=flat-square&logo=cursor)](https://cursor.com/en/install-mcp?name=awslabs.aurora-dsql-mcp-server&config=eyJjb21tYW5kIjoidXZ4IGF3c2xhYnMuYXVyb3JhLWRzcWwtbWNwLXNlcnZlckBsYXRlc3QgLS1jbHVzdGVyX2VuZHBvaW50IFt5b3VyIGRzcWwgY2x1c3RlciBlbmRwb2ludF0gLS1yZWdpb24gW3lvdXIgZHNxbCBjbHVzdGVyIHJlZ2lvbiwgZS5nLiB1cy1lYXN0LTFdIC0tZGF0YWJhc2VfdXNlciBbeW91ciBkc3FsIHVzZXJuYW1lXSAtLXByb2ZpbGUgZGVmYXVsdCIsImVudiI6eyJGQVNUTUNQX0xPR19MRVZFTCI6IkVSUk9SIn0sImRpc2FibGVkIjpmYWxzZSwiYXV0b0FwcHJvdmUiOltdfQ%3D%3D) <br/>[![Install on VS Code](https://img.shields.io/badge/Install-VS_Code-FF9900?style=flat-square&logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/redirect/mcp/install?name=Aurora%20DSQL%20MCP%20Server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.aurora-dsql-mcp-server%40latest%22%2C%22--cluster_endpoint%22%2C%22%5Byour%20dsql%20cluster%20endpoint%5D%22%2C%22--region%22%2C%22%5Byour%20dsql%20cluster%20region%2C%20e.g.%20us-east-1%5D%22%2C%22--database_user%22%2C%22%5Byour%20dsql%20username%5D%22%2C%22--profile%22%2C%22default%22%5D%2C%22env%22%3A%7B%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%7D%2C%22disabled%22%3Afalse%2C%22autoApprove%22%3A%5B%5D%7D) |
| [Amazon DocumentDB MCP Server](src/documentdb-mcp-server) | MongoDB 호환 문서 데이터베이스 작업 | [![Install](https://img.shields.io/badge/Install-Kiro-9046FF?style=flat-square&logo=kiro)](https://kiro.dev/launch/mcp/add?name=awslabs.documentdb-mcp-server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.documentdb-mcp-serve%40latest%22%5D%2C%22env%22%3A%7B%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%2C%22AWS_PROFILE%22%3A%22your-aws-profile%22%7D%7D) <br/>[![Install](https://img.shields.io/badge/Install-Cursor-blue?style=flat-square&logo=cursor)](https://cursor.com/en/install-mcp?name=awslabs.documentdb-mcp-server&config=eyJjb21tYW5kIjoidXZ4IGF3c2xhYnMuZG9jdW1lbnRkYi1tY3Atc2VydmVAbGF0ZXN0IiwiZW52Ijp7IkZBU1RNQ1BfTE9HX0xFVkVMIjoiRVJST1IiLCJBV1NfUFJPRklMRSI6InlvdXItYXdzLXByb2ZpbGUifSwiZGlzYWJsZWQiOmZhbHNlLCJhdXRvQXBwcm92ZSI6W119) <br/>[![Install on VS Code](https://img.shields.io/badge/Install-VS_Code-FF9900?style=flat-square&logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/redirect/mcp/install?name=DocumentDB%20MCP%20Server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.documentdb-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%2C%22AWS_PROFILE%22%3A%22your-aws-profile%22%7D%2C%22disabled%22%3Afalse%2C%22autoApprove%22%3A%5B%5D%7D) |
| [Amazon Neptune MCP Server](src/amazon-neptune-mcp-server) | openCypher 및 Gremlin을 사용한 그래프 데이터베이스 쿼리 | [![Install](https://img.shields.io/badge/Install-Kiro-9046FF?style=flat-square&logo=kiro)](https://kiro.dev/launch/mcp/add?name=awslabs.amazon-neptune-mcp-server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.amazon-neptune-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22NEPTUNE_ENDPOINT%22%3A%22https%3A//your-neptune-cluster-id.region.neptune.amazonaws.com%3A8182%22%2C%22AWS_PROFILE%22%3A%22your-aws-profile%22%2C%22AWS_REGION%22%3A%22us-east-1%22%2C%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%7D%7D) <br/>[![Install](https://img.shields.io/badge/Install-Cursor-blue?style=flat-square&logo=cursor)](https://cursor.com/en/install-mcp?name=awslabs.amazon-neptune-mcp-server&config=eyJjb21tYW5kIjoidXZ4IGF3c2xhYnMuYW1hem9uLW5lcHR1bmUtbWNwLXNlcnZlckBsYXRlc3QiLCJlbnYiOnsiTkVQVFVORV9FTkRQT0lOVCI6Imh0dHBzOi8veW91ci1uZXB0dW5lLWNsdXN0ZXItaWQucmVnaW9uLm5lcHR1bmUuYW1hem9uYXdzLmNvbTo4MTgyIiwiQVdTX1BST0ZJTEUiOiJ5b3VyLWF3cy1wcm9maWxlIiwiQVdTX1JFR0lPTiI6InVzLWVhc3QtMSIsIkZBU1RNQ1BfTE9HX0xFVkVMIjoiRVJST1IifSwiZGlzYWJsZWQiOmZhbHNlLCJhdXRvQXBwcm92ZSI6W119) <br/>[![Install on VS Code](https://img.shields.io/badge/Install-VS_Code-FF9900?style=flat-square&logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/redirect/mcp/install?name=Amazon%20Neptune%20MCP%20Server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.amazon-neptune-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22NEPTUNE_ENDPOINT%22%3A%22https%3A%2F%2Fyour-neptune-cluster-id.region.neptune.amazonaws.com%3A8182%22%2C%22AWS_PROFILE%22%3A%22your-aws-profile%22%2C%22AWS_REGION%22%3A%22us-east-1%22%2C%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%7D%2C%22disabled%22%3Afalse%2C%22autoApprove%22%3A%5B%5D%7D) |
| [Amazon Keyspaces MCP Server](src/amazon-keyspaces-mcp-server) | Apache Cassandra 호환 작업 | [![Install](https://img.shields.io/badge/Install-Kiro-9046FF?style=flat-square&logo=kiro)](https://kiro.dev/launch/mcp/add?name=awslabs.amazon-keyspaces-mcp-server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.amazon-keyspaces-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22AWS_PROFILE%22%3A%22your-aws-profile%22%2C%22AWS_REGION%22%3A%22us-east-1%22%2C%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%7D%7D) <br/>[![Install](https://img.shields.io/badge/Install-Cursor-blue?style=flat-square&logo=cursor)](https://cursor.com/en/install-mcp?name=awslabs.amazon-keyspaces-mcp-server&config=eyJjb21tYW5kIjoidXZ4IGF3c2xhYnMuYW1hem9uLWtleXNwYWNlcy1tY3Atc2VydmVyQGxhdGVzdCIsImVudiI6eyJBV1NfUFJPRklMRSI6InlvdXItYXdzLXByb2ZpbGUiLCJBV1NfUkVHSU9OIjoidXMtZWFzdC0xIiwiRkFTVE1DUF9MT0dfTEVWRUwiOiJFUlJPUiJ9LCJkaXNhYmxlZCI6ZmFsc2UsImF1dG9BcHByb3ZlIjpbXX0%3D) <br/>[![Install on VS Code](https://img.shields.io/badge/Install-VS_Code-FF9900?style=flat-square&logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/redirect/mcp/install?name=Amazon%20Keyspaces%20MCP%20Server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.amazon-keyspaces-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22AWS_PROFILE%22%3A%22your-aws-profile%22%2C%22AWS_REGION%22%3A%22us-east-1%22%2C%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%7D%2C%22disabled%22%3Afalse%2C%22autoApprove%22%3A%5B%5D%7D) |
| [Amazon Timestream for InfluxDB MCP Server](src/timestream-for-influxdb-mcp-server) | 시계열 데이터베이스 작업 및 InfluxDB 호환성 | [![Install](https://img.shields.io/badge/Install-Kiro-9046FF?style=flat-square&logo=kiro)](https://kiro.dev/launch/mcp/add?name=awslabs.timestream-for-influxdb-mcp-server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.timestream-for-influxdb-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22AWS_PROFILE%22%3A%22your-aws-profile%22%2C%22AWS_REGION%22%3A%22us-east-1%22%2C%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%7D%7D) <br/>[![Install](https://img.shields.io/badge/Install-Cursor-blue?style=flat-square&logo=cursor)](https://cursor.com/en/install-mcp?name=awslabs.timestream-for-influxdb-mcp-server&config=eyJjb21tYW5kIjoidXZ4IGF3c2xhYnMudGltZXN0cmVhbS1mb3ItaW5mbHV4ZGItbWNwLXNlcnZlckBsYXRlc3QiLCJlbnYiOnsiQVdTX1BST0ZJTEUiOiJ5b3VyLWF3cy1wcm9maWxlIiwiQVdTX1JFR0lPTiI6InVzLWVhc3QtMSIsIkZBU1RNQ1BfTE9HX0xFVkVMIjoiRVJST1IifSwiZGlzYWJsZWQiOmZhbHNlLCJhdXRvQXBwcm92ZSI6W119) <br/>[![Install on VS Code](https://img.shields.io/badge/Install-VS_Code-FF9900?style=flat-square&logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/redirect/mcp/install?name=Timestream%20for%20InfluxDB%20MCP%20Server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.timestream-for-influxdb-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22AWS_PROFILE%22%3A%22your-aws-profile%22%2C%22AWS_REGION%22%3A%22us-east-1%22%2C%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%7D%2C%22disabled%22%3Afalse%2C%22autoApprove%22%3A%5B%5D%7D) |
| [Amazon RDS MSSQL MCP Server](src/mssql-mcp-server)                                 | RDS Data API를 통한 SQL Server 데이터베이스 작업 | [![Install](https://img.shields.io/badge/Install-Kiro-9046FF?style=flat-square&logo=kiro)](https://kiro.dev/launch/mcp/add?name=awslabs.mssql-mcp-server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.mssql-mcp-server%40latest%22%2C%22--resource_arn%22%2C%22%5Byour%22%2C%22data%5D%22%2C%22--secret_arn%22%2C%22%5Byour%22%2C%22data%5D%22%2C%22--database%22%2C%22%5Byour%22%2C%22data%5D%22%2C%22--region%22%2C%22%5Byour%22%2C%22data%5D%22%2C%22--readonly%22%2C%22True%22%5D%2C%22env%22%3A%7B%22AWS_PROFILE%22%3A%22your-aws-profile%22%2C%22AWS_REGION%22%3A%22us-east-1%22%2C%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%7D%7D) <br/>[![Install](https://img.shields.io/badge/Install-Cursor-blue?style=flat-square&logo=cursor)](https://cursor.com/en/install-mcp?name=awslabs.mssql-mcp-server&config=eyJjb21tYW5kIjoidXZ4IGF3c2xhYnMubXNzcWwtbWNwLXNlcnZlckBsYXRlc3QgLS1yZXNvdXJjZV9hcm4gW3lvdXIgZGF0YV0gLS1zZWNyZXRfYXJuIFt5b3VyIGRhdGFdIC0tZGF0YWJhc2UgW3lvdXIgZGF0YV0gLS1yZWdpb24gW3lvdXIgZGF0YV0gLS1yZWFkb25seSBUcnVlIiwiZW52Ijp7IkFXU19QUk9GSUxFIjoieW91ci1hd3MtcHJvZmlsZSIsIkFXU19SRUdJT04iOiJ1cy1lYXN0LTEiLCJGQVNUTUNQX0xPR19MRVZFTCI6IkVSUk9SIn0sImRpc2FibGVkIjpmYWxzZSwiYXV0b0FwcHJvdmUiOltdJSAgICAgICAK%3D%3D) <br/>[![Install on VS Code](https://img.shields.io/badge/Install-VS_Code-FF9900?style=flat-square&logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/redirect/mcp/install?name=MSSQL%20MCP%20Server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.mssql-mcp-server%40latest%22%2C%22--resource_arn%22%2C%22%5Byour%20data%5D%22%2C%22--secret_arn%22%2C%22%5Byour%20data%5D%22%2C%22--database%22%2C%22%5Byour%20data%5D%22%2C%22--region%22%2C%22%5Byour%20data%5D%22%2C%22--readonly%22%2C%22True%22%5D%2C%22env%22%3A%7B%22AWS_PROFILE%22%3A%22your-aws-profile%22%2C%22AWS_REGION%22%3A%22us-east-1%22%2C%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%7D%2C%22disabled%22%3Afalse%2C%22autoApprove%22%3A%5B%5D%7D) |

| [Amazon RDS Oracle MCP Server](src/oracle-mcp-server) | Secrets Manager 인증을 통한 Oracle Database 작업 | [![Install](https://img.shields.io/badge/Install-Kiro-9046FF?style=flat-square&logo=kiro)](https://kiro.dev/launch/mcp/add?name=awslabs.oracle-mcp-server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.oracle-mcp-server%40latest%22%2C%22--db_endpoint%22%2C%22%5Byour%20data%5D%22%2C%22--secret_arn%22%2C%22%5Byour%20data%5D%22%2C%22--database%22%2C%22%5Byour%20data%5D%22%2C%22--region%22%2C%22%5Byour%20data%5D%22%5D%2C%22env%22%3A%7B%22AWS_PROFILE%22%3A%22your-aws-profile%22%2C%22AWS_REGION%22%3A%22us-east-1%22%2C%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%7D%7D) <br/>[![Install](https://img.shields.io/badge/Install-Cursor-blue?style=flat-square&logo=cursor)](https://cursor.com/en/install-mcp?name=awslabs.oracle-mcp-server&config=eyJjb21tYW5kIjogInV2eCBhd3NsYWJzLm9yYWNsZS1tY3Atc2VydmVyQGxhdGVzdCAtLWRiX2VuZHBvaW50IFt5b3VyIGRhdGFdIC0tc2VjcmV0X2FybiBbeW91ciBkYXRhXSAtLWRhdGFiYXNlIFt5b3VyIGRhdGFdIC0tcmVnaW9uIFt5b3VyIGRhdGFdIiwgImVudiI6IHsiQVdTX1BST0ZJTEUiOiAieW91ci1hd3MtcHJvZmlsZSIsICJBV1NfUkVHSU9OIjogInVzLWVhc3QtMSIsICJGQVNUTUNQX0xPR19MRVZFTCI6ICJFUlJPUiJ9LCAiZGlzYWJsZWQiOiBmYWxzZSwgImF1dG9BcHByb3ZlIjogW119) <br/>[![Install on VS Code](https://img.shields.io/badge/Install-VS_Code-FF9900?style=flat-square&logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/redirect/mcp/install?name=Oracle%20MCP%20Server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.oracle-mcp-server%40latest%22%2C%22--db_endpoint%22%2C%22%5Byour%20data%5D%22%2C%22--secret_arn%22%2C%22%5Byour%20data%5D%22%2C%22--database%22%2C%22%5Byour%20data%5D%22%2C%22--region%22%2C%22%5Byour%20data%5D%22%5D%2C%22env%22%3A%7B%22AWS_PROFILE%22%3A%22your-aws-profile%22%2C%22AWS_REGION%22%3A%22us-east-1%22%2C%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%7D%2C%22disabled%22%3Afalse%2C%22autoApprove%22%3A%5B%5D%7D) |

##### 캐싱 및 성능

| 서버 이름 | 설명 | 설치 |
|-------------|-------------|---------|
| [Amazon ElastiCache / MemoryDB for Valkey MCP Server](src/valkey-mcp-server) | Valkey를 활용한 고급 데이터 구조 및 캐싱 | [![Install](https://img.shields.io/badge/Install-Kiro-9046FF?style=flat-square&logo=kiro)](https://kiro.dev/launch/mcp/add?name=awslabs.valkey-mcp-server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.valkey-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22VALKEY_HOST%22%3A%22127.0.0.1%22%2C%22VALKEY_PORT%22%3A%226379%22%2C%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%7D%7D) <br/>[![Install](https://img.shields.io/badge/Install-Cursor-blue?style=flat-square&logo=cursor)](https://cursor.com/en/install-mcp?name=awslabs.valkey-mcp-server&config=eyJjb21tYW5kIjoidXZ4IGF3c2xhYnMudmFsa2V5LW1jcC1zZXJ2ZXJAbGF0ZXN0IiwiZW52Ijp7IlZBTEtFWV9IT1NUIjoiMTI3LjAuMC4xIiwiVkFMS0VZX1BPUlQiOiI2Mzc5IiwiRkFTVE1DUF9MT0dfTEVWRUwiOiJFUlJPUiJ9LCJhdXRvQXBwcm92ZSI6W10sImRpc2FibGVkIjpmYWxzZX0%3D) <br/>[![Install on VS Code](https://img.shields.io/badge/Install-VS_Code-FF9900?style=flat-square&logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/redirect/mcp/install?name=Valkey%20MCP%20Server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.valkey-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22VALKEY_HOST%22%3A%22127.0.0.1%22%2C%22VALKEY_PORT%22%3A%226379%22%2C%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%7D%2C%22autoApprove%22%3A%5B%5D%2C%22disabled%22%3Afalse%7D) |
| [Amazon ElastiCache for Memcached MCP Server ](src/memcached-mcp-server) | Memcached 프로토콜을 사용한 고속 캐싱 | [![Install](https://img.shields.io/badge/Install-Kiro-9046FF?style=flat-square&logo=kiro)](https://kiro.dev/launch/mcp/add?name=awslabs.memcached-mcp-server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.memcached-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%2C%22MEMCACHED_HOST%22%3A%22your-memcached-host%22%2C%22MEMCACHED_PORT%22%3A%2211211%22%7D%7D) <br/>[![Install](https://img.shields.io/badge/Install-Cursor-blue?style=flat-square&logo=cursor)](https://cursor.com/en/install-mcp?name=awslabs.memcached-mcp-server&config=eyJjb21tYW5kIjoidXZ4IGF3c2xhYnMubWVtY2FjaGVkLW1jcC1zZXJ2ZXJAbGF0ZXN0IiwiZW52Ijp7IkZBU1RNQ1BfTE9HX0xFVkVMIjoiRVJST1IiLCJNRU1DQUNIRURfSE9TVCI6InlvdXItbWVtY2FjaGVkLWhvc3QiLCJNRU1DQUNIRURfUE9SVCI6IjExMjExIn0sImRpc2FibGVkIjpmYWxzZSwiYXV0b0FwcHJvdmUiOltdfQ%3D%3D) <br/>[![Install on VS Code](https://img.shields.io/badge/Install-VS_Code-FF9900?style=flat-square&logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/redirect/mcp/install?name=Memcached%20MCP%20Server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.memcached-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%2C%22MEMCACHED_HOST%22%3A%22your-memcached-host%22%2C%22MEMCACHED_PORT%22%3A%2211211%22%7D%2C%22disabled%22%3Afalse%2C%22autoApprove%22%3A%5B%5D%7D) |

##### 워크플로 및 통합

| 서버 이름 | 설명 | 설치 |
|-------------|-------------|---------|
| [AWS Lambda Tool MCP Server](src/lambda-tool-mcp-server) | 프라이빗 리소스 접근을 위해 Lambda 함수를 AI 도구로 실행 | [![Install](https://img.shields.io/badge/Install-Kiro-9046FF?style=flat-square&logo=kiro)](https://kiro.dev/launch/mcp/add?name=awslabs.lambda-tool-mcp-server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.lambda-tool-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22AWS_PROFILE%22%3A%22your-aws-profile%22%2C%22AWS_REGION%22%3A%22us-east-1%22%2C%22FUNCTION_PREFIX%22%3A%22your-function-prefix%22%2C%22FUNCTION_LIST%22%3A%22your-first-function%2C%20your-second-function%22%2C%22FUNCTION_TAG_KEY%22%3A%22your-tag-key%22%2C%22FUNCTION_TAG_VALUE%22%3A%22your-tag-value%22%2C%22FUNCTION_INPUT_SCHEMA_ARN_TAG_KEY%22%3A%22your-function-tag-for-input-schema%22%7D%7D) <br/>[![Install](https://img.shields.io/badge/Install-Cursor-blue?style=flat-square&logo=cursor)](https://cursor.com/en/install-mcp?name=awslabs.lambda-tool-mcp-server&config=eyJjb21tYW5kIjoidXZ4IGF3c2xhYnMubGFtYmRhLXRvb2wtbWNwLXNlcnZlckBsYXRlc3QiLCJlbnYiOnsiQVdTX1BST0ZJTEUiOiJ5b3VyLWF3cy1wcm9maWxlIiwiQVdTX1JFR0lPTiI6InVzLWVhc3QtMSIsIkZVTkNUSU9OX1BSRUZJWCI6InlvdXItZnVuY3Rpb24tcHJlZml4IiwiRlVOQ1RJT05fTElTVCI6InlvdXItZmlyc3QtZnVuY3Rpb24sIHlvdXItc2Vjb25kLWZ1bmN0aW9uIiwiRlVOQ1RJT05fVEFHX0tFWSI6InlvdXItdGFnLWtleSIsIkZVTkNUSU9OX1RBR19WQUxVRSI6InlvdXItdGFnLXZhbHVlIiwiRlVOQ1RJT05fSU5QVVRfU0NIRU1BX0FSTl9UQUdfS0VZIjoieW91ci1mdW5jdGlvbi10YWctZm9yLWlucHV0LXNjaGVtYSJ9fQ%3D%3D) <br/>[![Install on VS Code](https://img.shields.io/badge/Install-VS_Code-FF9900?style=flat-square&logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/redirect/mcp/install?name=AWS%20Lambda%20Tool%20MCP%20Server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.lambda-tool-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22AWS_PROFILE%22%3A%22your-aws-profile%22%2C%22AWS_REGION%22%3A%22us-east-1%22%2C%22FUNCTION_PREFIX%22%3A%22your-function-prefix%22%2C%22FUNCTION_LIST%22%3A%22your-first-function%2C%20your-second-function%22%2C%22FUNCTION_TAG_KEY%22%3A%22your-tag-key%22%2C%22FUNCTION_TAG_VALUE%22%3A%22your-tag-value%22%2C%22FUNCTION_INPUT_SCHEMA_ARN_TAG_KEY%22%3A%22your-function-tag-for-input-schema%22%7D%7D) |
| [AWS Step Functions Tool MCP Server](src/stepfunctions-tool-mcp-server) | 복잡한 워크플로 및 비즈니스 프로세스 실행 | [![Install](https://img.shields.io/badge/Install-Kiro-9046FF?style=flat-square&logo=kiro)](https://kiro.dev/launch/mcp/add?name=awslabs.stepfunctions-tool-mcp-server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.stepfunctions-tool-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22AWS_PROFILE%22%3A%22your-aws-profile%22%2C%22AWS_REGION%22%3A%22us-east-1%22%2C%22STATE_MACHINE_PREFIX%22%3A%22your-state-machine-prefix%22%2C%22STATE_MACHINE_LIST%22%3A%22your-first-state-machine%2C%20your-second-state-machine%22%2C%22STATE_MACHINE_TAG_KEY%22%3A%22your-tag-key%22%2C%22STATE_MACHINE_TAG_VALUE%22%3A%22your-tag-value%22%2C%22STATE_MACHINE_INPUT_SCHEMA_ARN_TAG_KEY%22%3A%22your-state-machine-tag-for-input-schema%22%7D%7D) <br/>[![Install](https://img.shields.io/badge/Install-Cursor-blue?style=flat-square&logo=cursor)](https://cursor.com/en/install-mcp?name=awslabs.stepfunctions-tool-mcp-server&config=eyJjb21tYW5kIjoidXZ4IGF3c2xhYnMuc3RlcGZ1bmN0aW9ucy10b29sLW1jcC1zZXJ2ZXJAbGF0ZXN0IiwiZW52Ijp7IkFXU19QUk9GSUxFIjoieW91ci1hd3MtcHJvZmlsZSIsIkFXU19SRUdJT04iOiJ1cy1lYXN0LTEiLCJTVEFURV9NQUNISU5FX1BSRUZJWCI6InlvdXItc3RhdGUtbWFjaGluZS1wcmVmaXgiLCJTVEFURV9NQUNISU5FX0xJU1QiOiJ5b3VyLWZpcnN0LXN0YXRlLW1hY2hpbmUsIHlvdXItc2Vjb25kLXN0YXRlLW1hY2hpbmUiLCJTVEFURV9NQUNISU5FX1RBR19LRVkiOiJ5b3VyLXRhZy1rZXkiLCJTVEFURV9NQUNISU5FX1RBR19WQUxVRSI6InlvdXItdGFnLXZhbHVlIiwiU1RBVEVfTUFDSElORV9JTlBVVF9TQ0hFTUFfQVJOX1RBR19LRVkiOiJ5b3VyLXN0YXRlLW1hY2hpbmUtdGFnLWZvci1pbnB1dC1zY2hlbWEifX0%3D) <br/>[![Install on VS Code](https://img.shields.io/badge/Install-VS_Code-FF9900?style=flat-square&logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/redirect/mcp/install?name=Step%20Functions%20Tool%20MCP%20Server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.stepfunctions-tool-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22AWS_PROFILE%22%3A%22your-aws-profile%22%2C%22AWS_REGION%22%3A%22us-east-1%22%2C%22STATE_MACHINE_PREFIX%22%3A%22your-state-machine-prefix%22%2C%22STATE_MACHINE_LIST%22%3A%22your-first-state-machine%2C%20your-second-state-machine%22%2C%22STATE_MACHINE_TAG_KEY%22%3A%22your-tag-key%22%2C%22STATE_MACHINE_TAG_VALUE%22%3A%22your-tag-value%22%2C%22STATE_MACHINE_INPUT_SCHEMA_ARN_TAG_KEY%22%3A%22your-state-machine-tag-for-input-schema%22%7D%2C%22disabled%22%3Afalse%2C%22autoApprove%22%3A%5B%5D%7D) |
| [Amazon SNS/SQS MCP Server](src/amazon-sns-sqs-mcp-server) | 이벤트 기반 메시징 및 큐 관리 | [![Install](https://img.shields.io/badge/Install-Kiro-9046FF?style=flat-square&logo=kiro)](https://kiro.dev/launch/mcp/add?name=awslabs.amazon-sns-sqs-mcp-server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.amazon-sns-sqs-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22AWS_PROFILE%22%3A%22your-aws-profile%22%2C%22AWS_REGION%22%3A%22us-east-1%22%7D%7D) <br/>[![Install](https://img.shields.io/badge/Install-Cursor-blue?style=flat-square&logo=cursor)](https://cursor.com/en/install-mcp?name=awslabs.amazon-sns-sqs-mcp-server&config=eyJjb21tYW5kIjoidXZ4IGF3c2xhYnMuYW1hem9uLXNucy1zcXMtbWNwLXNlcnZlckBsYXRlc3QiLCJlbnYiOnsiQVdTX1BST0ZJTEUiOiJ5b3VyLWF3cy1wcm9maWxlIiwiQVdTX1JFR0lPTiI6InVzLWVhc3QtMSJ9fQ%3D%3D) <br/>[![Install on VS Code](https://img.shields.io/badge/Install-VS_Code-FF9900?style=flat-square&logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/redirect/mcp/install?name=Amazon%20SNS%2FSQS%20MCP%20Server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.amazon-sns-sqs-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22AWS_PROFILE%22%3A%22your-aws-profile%22%2C%22AWS_REGION%22%3A%22us-east-1%22%7D%7D) |
| [Amazon MQ MCP Server](src/amazon-mq-mcp-server) | RabbitMQ 및 ActiveMQ 메시지 브로커 관리 | [![Install](https://img.shields.io/badge/Install-Kiro-9046FF?style=flat-square&logo=kiro)](https://kiro.dev/launch/mcp/add?name=awslabs.amazon-mq-mcp-server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.amazon-mq-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22AWS_PROFILE%22%3A%22your-aws-profile%22%2C%22AWS_REGION%22%3A%22us-east-1%22%2C%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%7D%7D) <br/>[![Install](https://img.shields.io/badge/Install-Cursor-blue?style=flat-square&logo=cursor)](https://cursor.com/en/install-mcp?name=awslabs.amazon-mq-mcp-server&config=eyJjb21tYW5kIjoidXZ4IGF3c2xhYnMuYW1hem9uLW1xLW1jcC1zZXJ2ZXJAbGF0ZXN0IiwiZW52Ijp7IkFXU19QUk9GSUxFIjoieW91ci1hd3MtcHJvZmlsZSIsIkFXU19SRUdJT04iOiJ1cy1lYXN0LTEiLCJGQVNUTUNQX0xPR19MRVZFTCI6IkVSUk9SIn0sImRpc2FibGVkIjpmYWxzZSwiYXV0b0FwcHJvdmUiOltdfQ%3D%3D) <br/>[![Install on VS Code](https://img.shields.io/badge/Install-VS_Code-FF9900?style=flat-square&logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/redirect/mcp/install?name=Amazon%20MQ%20MCP%20Server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.amazon-mq-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22AWS_PROFILE%22%3A%22your-aws-profile%22%2C%22AWS_REGION%22%3A%22us-east-1%22%2C%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%7D%2C%22disabled%22%3Afalse%2C%22autoApprove%22%3A%5B%5D%7D) |

##### 운영 및 모니터링

| 서버 이름 | 설명 | 설치 |
|-------------|-------------|---------|
| [Amazon CloudWatch MCP Server](src/cloudwatch-mcp-server) | 지표, 경보, 로그 분석 및 운영 트러블슈팅 | [![Install](https://img.shields.io/badge/Install-Kiro-9046FF?style=flat-square&logo=kiro)](https://kiro.dev/launch/mcp/add?name=awslabs.cloudwatch-mcp-server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.cloudwatch-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22AWS_PROFILE%22%3A%22%5BThe%20AWS%20Profile%20Name%20to%20use%20for%20AWS%20access%5D%22%2C%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%7D%7D) <br/>[![Install](https://img.shields.io/badge/Install-Cursor-blue?style=flat-square&logo=cursor)](https://cursor.com/en/install-mcp?name=awslabs.cloudwatch-mcp-server&config=ewogICAgImF1dG9BcHByb3ZlIjogW10sCiAgICAiZGlzYWJsZWQiOiBmYWxzZSwKICAgICJjb21tYW5kIjogInV2eCBhd3NsYWJzLmNsb3Vkd2F0Y2gtbWNwLXNlcnZlckBsYXRlc3QiLAogICAgImVudiI6IHsKICAgICAgIkFXU19QUk9GSUxFIjogIltUaGUgQVdTIFByb2ZpbGUgTmFtZSB0byB1c2UgZm9yIEFXUyBhY2Nlc3NdIiwKICAgICAgIkZBU1RNQ1BfTE9HX0xFVkVMIjogIkVSUk9SIgogICAgfSwKICAgICJ0cmFuc3BvcnRUeXBlIjogInN0ZGlvIgp9) <br/>[![Install on VS Code](https://img.shields.io/badge/Install-VS_Code-FF9900?style=flat-square&logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/redirect/mcp/install?name=CloudWatch%20MCP%20Server&config=%7B%22autoApprove%22%3A%5B%5D%2C%22disabled%22%3Afalse%2C%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.cloudwatch-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22AWS_PROFILE%22%3A%22%5BThe%20AWS%20Profile%20Name%20to%20use%20for%20AWS%20access%5D%22%2C%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%7D%2C%22transportType%22%3A%22stdio%22%7D) |
| [Amazon CloudWatch Application Signals MCP Server](src/cloudwatch-applicationsignals-mcp-server) | 애플리케이션 모니터링 및 성능 인사이트 | [![Install](https://img.shields.io/badge/Install-Kiro-9046FF?style=flat-square&logo=kiro)](https://kiro.dev/launch/mcp/add?name=applicationsignals&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.cloudwatch-applicationsignals-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22AWS_PROFILE%22%3A%22%5BThe%20AWS%20Profile%20Name%20to%20use%20for%20AWS%20access%5D%22%2C%22AWS_REGION%22%3A%22%5BThe%20AWS%20region%20to%20run%20in%5D%22%2C%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%7D%7D) <br/>[![Install](https://img.shields.io/badge/Install-Cursor-blue?style=flat-square&logo=cursor)](https://cursor.com/en/install-mcp?name=applicationsignals&config=eyJhdXRvQXBwcm92ZSI6W10sImRpc2FibGVkIjpmYWxzZSwidGltZW91dCI6NjAsImNvbW1hbmQiOiJ1dnggYXdzbGFicy5jbG91ZHdhdGNoLWFwcGxpY2F0aW9uc2lnbmFscy1tY3Atc2VydmVyQGxhdGVzdCIsImVudiI6eyJBV1NfUFJPRklMRSI6IltUaGUgQVdTIFByb2ZpbGUgTmFtZSB0byB1c2UgZm9yIEFXUyBhY2Nlc3NdIiwiQVdTX1JFR0lPTiI6IltUaGUgQVdTIHJlZ2lvbiB0byBydW4gaW5dIiwiRkFTVE1DUF9MT0dfTEVWRUwiOiJFUlJPUiJ9LCJ0cmFuc3BvcnRUeXBlIjoic3RkaW8ifQ) <br/>[![Install on VS Code](https://img.shields.io/badge/Install-VS_Code-FF9900?style=flat-square&logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/redirect/mcp/install?name=applicationsignals&config=%7B%22autoApprove%22%3A%5B%5D%2C%22disabled%22%3Afalse%2C%22timeout%22%3A60%2C%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.cloudwatch-applicationsignals-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22AWS_PROFILE%22%3A%22%5BThe%20AWS%20Profile%20Name%20to%20use%20for%20AWS%20access%5D%22%2C%22AWS_REGION%22%3A%22%5BThe%20AWS%20region%20to%20run%20in%5D%22%2C%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%7D%2C%22transportType%22%3A%22stdio%22%7D) |
| [AWS Managed Prometheus MCP Server](src/prometheus-mcp-server) | Prometheus 호환 작업 및 모니터링 | [![Install](https://img.shields.io/badge/Install-Kiro-9046FF?style=flat-square&logo=kiro)](https://kiro.dev/launch/mcp/add?name=awslabs.prometheus-mcp-server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.prometheus-mcp-server%40latest%22%2C%22--url%22%2C%22https%3A//aps-workspaces.us-east-1.amazonaws.com/workspaces/ws-%3CWorkspace%22%2C%22ID%3E%22%2C%22--region%22%2C%22%3CYour%22%2C%22AWS%22%2C%22Region%3E%22%2C%22--profile%22%2C%22%3CYour%22%2C%22CLI%22%2C%22Profile%22%2C%22%5Bdefault%5D%22%2C%22if%22%2C%22no%22%2C%22profile%22%2C%22is%22%2C%22used%3E%22%5D%2C%22env%22%3A%7B%22FASTMCP_LOG_LEVEL%22%3A%22DEBUG%22%2C%22AWS_PROFILE%22%3A%22%3CYour%20CLI%20Profile%20%5Bdefault%5D%20if%20no%20profile%20is%20used%3E%22%7D%7D) <br/>[![Install](https://img.shields.io/badge/Install-Cursor-blue?style=flat-square&logo=cursor)](https://cursor.com/en/install-mcp?name=awslabs.prometheus-mcp-server&config=eyJjb21tYW5kIjoidXZ4IGF3c2xhYnMucHJvbWV0aGV1cy1tY3Atc2VydmVyQGxhdGVzdCAtLXVybCBodHRwczovL2Fwcy13b3Jrc3BhY2VzLnVzLWVhc3QtMS5hbWF6b25hd3MuY29tL3dvcmtzcGFjZXMvd3MtPFdvcmtzcGFjZSBJRD4gLS1yZWdpb24gPFlvdXIgQVdTIFJlZ2lvbj4gLS1wcm9maWxlIDxZb3VyIENMSSBQcm9maWxlIFtkZWZhdWx0XSBpZiBubyBwcm9maWxlIGlzIHVzZWQ%2BIiwiZW52Ijp7IkZBU1RNQ1BfTE9HX0xFVkVMIjoiREVCVUciLCJBV1NfUFJPRklMRSI6IjxZb3VyIENMSSBQcm9maWxlIFtkZWZhdWx0XSBpZiBubyBwcm9maWxlIGlzIHVzZWQ%2BIn19) <br/>[![Install on VS Code](https://img.shields.io/badge/Install-VS_Code-FF9900?style=flat-square&logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/redirect/mcp/install?name=Prometheus%20MCP%20Server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.prometheus-mcp-server%40latest%22%2C%22--url%22%2C%22https%3A%2F%2Faps-workspaces.us-east-1.amazonaws.com%2Fworkspaces%2Fws-%3CWorkspace%20ID%3E%22%2C%22--region%22%2C%22%3CYour%20AWS%20Region%3E%22%2C%22--profile%22%2C%22%3CYour%20CLI%20Profile%20%5Bdefault%5D%20if%20no%20profile%20is%20used%3E%22%5D%2C%22env%22%3A%7B%22FASTMCP_LOG_LEVEL%22%3A%22DEBUG%22%2C%22AWS_PROFILE%22%3A%22%3CYour%20CLI%20Profile%20%5Bdefault%5D%20if%20no%20profile%20is%20used%3E%22%7D%7D) |
| [AWS Security Agent MCP Server](src/security-agent-mcp-server) | AWS Security Agent를 활용한 자동화된 보안 스캐닝, 침투 테스트, 조치 | |
| [AWS Well-Architected Security Assessment Tool MCP Server](src/well-architected-security-mcp-server) | Well-Architected Framework 보안 원칙(Security Pillar) 기준으로 AWS 환경 평가 | [![Install](https://img.shields.io/badge/Install-Kiro-9046FF?style=flat-square&logo=kiro)](https://kiro.dev/launch/mcp/add?name=awslabs.well-architected-security-mcp-server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.well-architected-security-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22AWS_PROFILE%22%3A%22your-aws-profile%22%2C%22AWS_REGION%22%3A%22us-east-1%22%2C%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%7D%7D) <br/>[![Install](https://img.shields.io/badge/Install-Cursor-blue?style=flat-square&logo=cursor)](https://cursor.com/en/install-mcp?name=awslabs.well-architected-security-mcp-server&config=eyJjb21tYW5kIjoidXZ4IGF3c2xhYnMud2VsbC1hcmNoaXRlY3RlZC1zZWN1cml0eS1tY3Atc2VydmVyQGxhdGVzdCIsImVudiI6eyJBV1NfUFJPRklMRSI6InlvdXItYXdzLXByb2ZpbGUiLCJBV1NfUkVHSU9OIjoidXMtZWFzdC0xIiwiRkFTVE1DUF9MT0dfTEVWRUwiOiJFUlJPUiJ9LCJkaXNhYmxlZCI6ZmFsc2UsImF1dG9BcHByb3ZlIjpbXX0K) <br/>[![Install on VS Code](https://img.shields.io/badge/Install-VS_Code-FF9900?style=flat-square&logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/redirect/mcp/install?name=AWS%20Well-Architected%20Security%20Assessment%20Tool%20MCP%20Server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.well-architected-security-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22AWS_PROFILE%22%3A%22your-aws-profile%22%2C%22AWS_REGION%22%3A%22us-east-1%22%2C%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%7D%2C%22disabled%22%3Afalse%2C%22autoApprove%22%3A%5B%5D%7D) |
| [AWS CloudTrail MCP Server](src/cloudtrail-mcp-server/) | CloudTrail 이벤트 쿼리 및 분석 | [![Install](https://img.shields.io/badge/Install-Kiro-9046FF?style=flat-square&logo=kiro)](https://kiro.dev/launch/mcp/add?name=awslabs.cloudtrail-mcp-server&config=%7B%22command%22%3A%22docker%22%2C%22args%22%3A%5B%22run%22%2C%22--rm%22%2C%22--interactive%22%2C%22-e%20AWS_PROFILE%3D%5BThe%20AWS%20Profile%20Name%5D%22%2C%22awslabs/cloudtrail-mcp-server%3Alatest%22%5D%2C%22env%22%3A%7B%7D%7D) <br/>[![Install](https://img.shields.io/badge/Install-Cursor-blue?style=flat-square&logo=cursor)](https://www.cursor.com/install-mcp?name=awslabs.cloudtrail-mcp-server&config=ewogICAgICAgICJjb21tYW5kIjogImRvY2tlciIsCiAgICAgICAgImFyZ3MiOiBbCiAgICAgICAgICAicnVuIiwKICAgICAgICAgICItLXJtIiwKICAgICAgICAgICItLWludGVyYWN0aXZlIiwKICAgICAgICAgICItZSBBV1NfUFJPRklMRT1bVGhlIEFXUyBQcm9maWxlIE5hbWVdIiwKICAgICAgICAgICJhd3NsYWJzL2Nsb3VkdHJhaWwtbWNwLXNlcnZlcjpsYXRlc3QiCiAgICAgICAgXSwKICAgICAgICAiZW52Ijoge30sCiAgICAgICAgImRpc2FibGVkIjogZmFsc2UsCiAgICAgICAgImF1dG9BcHByb3ZlIjogW10KfQ==) <br/>[![Install on VS Code](https://img.shields.io/badge/Install_on-VS_Code-FF9900?style=flat-square&logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/redirect/mcp/install?name=CloudTrail%20MCP%20Server&config=%7B%22autoApprove%22%3A%5B%5D%2C%22disabled%22%3Afalse%2C%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.cloudtrail-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22AWS_PROFILE%22%3A%22%5BThe%20AWS%20Profile%20Name%20to%20use%20for%20AWS%20access%5D%22%2C%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%7D%2C%22transportType%22%3A%22stdio%22%7D) |
| [AWS Systems Manager for SAP MCP Server](src/aws-for-sap-management-mcp-server) | 상태 확인, 구성 검증, 스케줄링을 통해 AWS의 SAP 애플리케이션을 관리, 모니터링, 운영 | [![Install](https://img.shields.io/badge/Install-Kiro-9046FF?style=flat-square&logo=kiro)](https://kiro.dev/launch/mcp/add?name=awslabs.aws-for-sap-management-mcp-server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.aws-for-sap-management-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22AWS_PROFILE%22%3A%22your-aws-profile%22%2C%22AWS_REGION%22%3A%22us-east-1%22%2C%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%7D%7D) <br/>[![Install](https://img.shields.io/badge/Install-Cursor-blue?style=flat-square&logo=cursor)](https://cursor.com/en/install-mcp?name=awslabs.aws-for-sap-management-mcp-server&config=eyJjb21tYW5kIjogInV2eCIsICJhcmdzIjogWyJhd3NsYWJzLmF3cy1mb3Itc2FwLW1hbmFnZW1lbnQtbWNwLXNlcnZlckBsYXRlc3QiXSwgImVudiI6IHsiQVdTX1BST0ZJTEUiOiAieW91ci1hd3MtcHJvZmlsZSIsICJBV1NfUkVHSU9OIjogInVzLWVhc3QtMSIsICJGQVNUTUNQX0xPR19MRVZFTCI6ICJFUlJPUiJ9LCAiZGlzYWJsZWQiOiBmYWxzZSwgImF1dG9BcHByb3ZlIjogW119) <br/>[![Install on VS Code](https://img.shields.io/badge/Install-VS_Code-FF9900?style=flat-square&logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/redirect/mcp/install?name=AWS%20For%20SAP%20Management%20MCP%20Server&config=%7B%22command%22%3A%20%22uvx%22%2C%20%22args%22%3A%20%5B%22awslabs.aws-for-sap-management-mcp-server%40latest%22%5D%2C%20%22env%22%3A%20%7B%22AWS_PROFILE%22%3A%20%22your-aws-profile%22%2C%20%22AWS_REGION%22%3A%20%22us-east-1%22%2C%20%22FASTMCP_LOG_LEVEL%22%3A%20%22ERROR%22%7D%2C%20%22disabled%22%3A%20false%2C%20%22autoApprove%22%3A%20%5B%5D%7D) |

## MCP AWS Lambda 핸들러 모듈

AWS Lambda를 사용해 Model Context Protocol(MCP)용 서버리스 HTTP 핸들러를 만들기 위한 Python 라이브러리입니다. 이 모듈은 플러그인 방식의 세션 관리(기본 DynamoDB 지원 포함)를 갖춘 MCP HTTP 엔드포인트 구축용 유연한 프레임워크를 제공합니다.

**주요 기능:**

- AWS Lambda를 사용한 간편한 서버리스 MCP HTTP 핸들러 생성
- 플러그인 방식의 세션 관리 시스템
- 기본 제공 DynamoDB 세션 백엔드 지원
- 사용자 지정 가능한 인증 및 권한 부여
- 예제 구현 및 테스트

전체 사용법, 설치, 개발 방법은 [`src/mcp-lambda-handler/README.md`](src/mcp-lambda-handler/README.md)를 참고하세요.

## 로컬 MCP 서버와 원격 MCP 서버는 각각 언제 사용하나요?

MCP 서버는 개발 머신에서 로컬로 실행하거나 클라우드에서 원격으로 실행할 수 있습니다. 각 방식이 적합한 경우는 다음과 같습니다:

### 로컬 MCP 서버
- **개발 및 테스트**: 로컬 개발, 테스트, 디버깅에 적합
- **오프라인 작업**: 인터넷 연결이 제한된 환경에서도 작업 지속
- **데이터 프라이버시**: 민감한 데이터와 자격 증명을 로컬 머신에 보관
- **낮은 지연 시간**: 네트워크 오버헤드를 최소화하여 더 빠른 응답 속도
- **리소스 제어**: 서버 리소스와 구성을 직접 제어

### 원격 MCP 서버
- **팀 협업**: 팀 전체에서 일관된 서버 구성 공유
- **리소스 집약적 작업**: 무거운 처리를 전용 클라우드 리소스로 오프로드
- **상시 가용성**: 어디서나 어떤 디바이스에서든 MCP 서버에 접근
- **자동 업데이트**: 최신 기능과 보안 패치를 자동으로 적용
- **확장성**: 로컬 리소스 제약 없이 변동하는 워크로드를 손쉽게 처리
- **보안**: IAM 기반 권한과 자격 증명 노출 없는 중앙 집중식 보안 제어
- **거버넌스**: 엔터프라이즈급 거버넌스를 위한 포괄적인 감사 로깅 및 컴플라이언스 모니터링

> **참고**: [공식 AWS MCP 서버](https://docs.aws.amazon.com/aws-mcp/latest/userguide/what-is-mcp-server.html)(프리뷰)와 AWS Knowledge MCP처럼 일부 MCP 서버는 AWS가 완전 관리형 서비스로 제공합니다. 이러한 AWS 관리형 원격 서버는 별도의 설정이나 인프라 관리가 필요 없으며, 연결하기만 하면 바로 사용할 수 있습니다.

## 서버 활용 사례

예를 들어 **AWS Documentation MCP Server**를 사용하면 AI 어시스턴트가 Amazon Bedrock Inline 에이전트와 같은 모든 AWS 서비스에 대해 최신 정보를 조사하고 코드를 생성하도록 도울 수 있습니다. 또는 **CDK MCP Server**나 **Terraform MCP Server**를 사용하여 AI 어시스턴트가 최신 API를 사용하고 AWS 모범 사례를 따르는 코드형 인프라 구현을 작성하게 할 수 있습니다. **AWS Pricing MCP Server**를 사용하면 "이 CDK 프로젝트를 배포하기 전 예상 월 비용은 얼마인가요?" 또는 "이 인프라 설계에서 발생할 수 있는 AWS 서비스 비용을 이해하도록 도와줄 수 있나요?"와 같이 질문하고 상세한 비용 추정과 예산 계획 인사이트를 받을 수 있습니다. **Valkey MCP Server**는 Valkey 데이터 스토어와의 자연어 상호 작용을 지원하여, AI 어시스턴트가 간단한 대화형 인터페이스로 데이터 작업을 효율적으로 관리할 수 있게 합니다.

## 설치 및 설정

각 서버에는 Kiro, Cursor, VSCode용 원클릭 설치를 포함한 개별 설치 안내가 있습니다. 일반적인 절차는 다음과 같습니다:

1. [Astral](https://docs.astral.sh/uv/getting-started/installation/)에서 `uv` 설치
2. `uv python install 3.10` 명령으로 Python 설치
3. 필요한 서비스에 접근할 수 있는 AWS 자격 증명 구성
4. MCP 클라이언트 구성에 서버 추가

Kiro MCP 설정(`~/.kiro/settings/mcp.json`) 구성 예시:

### macOS/Linux용 설정

```json
{
  "mcpServers": {
    "awslabs-core-mcp-server": {
      "command": "uvx",
      "args": [
        "awslabs.core-mcp-server@latest"
      ],
      "env": {
        "FASTMCP_LOG_LEVEL": "ERROR"
      }
    }
  }
}
```

구체적인 요구 사항과 구성 옵션은 각 서버의 README를 참고하세요.

### Windows용 설정

Windows에서 MCP 서버를 구성할 때는 약간 다른 구성 형식을 사용해야 합니다:

```json
{
  "mcpServers": {
    "awslabs-core-mcp-server": {
      "disabled": false,
      "timeout": 60,
      "type": "stdio",
      "command": "uv",
      "args": [
        "tool",
        "run",
        "--from",
        "awslabs.core-mcp-server@latest",
        "awslabs.core-mcp-server.exe"
      ],
      "env": {
        "FASTMCP_LOG_LEVEL": "ERROR"
      }
    }
  }
}
```

MCP 구성에 문제가 있거나 적절한 파라미터가 설정되었는지 확인하려면 다음을 시도해 보세요:

```shell
# 15초 타임아웃으로 MCP 서버를 수동 실행
$ timeout 15s uv tool run <MCP Name> <args> 2>&1 || echo "Command completed or timed out"

# 예시 (Aurora MySQL MCP Server)
$ timeout 15s uv tool run awslabs.mysql-mcp-server --resource_arn <Your Resource ARN> --secret_arn <Your Secret ARN> ... 2>&1 || echo "Command completed or timed out"

# 인수가 올바르게 설정되지 않으면 다음과 같은 메시지가 표시될 수 있습니다:
usage: awslabs.mysql-mcp-server [-h] --resource_arn RESOURCE_ARN --secret_arn SECRET_ARN --database DATABASE
                                --region REGION --readonly READONLY
awslabs.mysql-mcp-server: error: the following arguments are required: --resource_arn, --secret_arn, --database, --region, --readonly
```

**`uvx`에 *"@latest"* 접미사를 사용할 때의 성능 참고 사항:**

*"@latest"* 접미사를 사용하면 MCP 클라이언트를 시작할 때마다 pypi에서 최신 MCP 서버 패키지를 확인하고 다운로드하지만, 초기 로딩 시간이 길어지는 비용이 발생합니다. 초기 로딩 시간을 최소화하려면 *"@latest"*를 제거하고 다음 방법 중 하나로 uv 캐시를 직접 관리하세요:

- `uv cache clean <tool>`: 여기서 {tool}은 캐시에서 삭제하고 다시 설치할 MCP 서버입니다(예: "awslabs.lambda-tool-mcp-server"). '<>'는 제거해야 합니다.
- `uvx <tool>@latest`: 도구를 최신 버전으로 갱신하고 uv 캐시에 추가합니다.

### 컨테이너에서 MCP 서버 실행하기

각 MCP 서버의 Docker 이미지는 [공개 AWS ECR 레지스트리](https://gallery.ecr.aws/awslabs-mcp)에 게시됩니다.

*이 예시는 "awslabs.aws-documentation-mcp-server"를 docker로 실행하는 방법이며, 다른 MCP 서버에도 동일하게 적용할 수 있습니다*

- 필요하다면 민감한 환경 변수를 파일에 저장합니다:

  ```.env
  # 가상의 AWS 임시 자격 증명이 담긴 .env 파일 내용 예시
  AWS_ACCESS_KEY_ID=ASIAIOSFODNN7EXAMPLE
  AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
  AWS_SESSION_TOKEN=AQoEXAMPLEH4aoAH0gNCAPy...truncated...zrkuWJOgQs8IZZaIv2BXIa2R4Olgk
  ```

- 컨테이너 내부에서는 `"env": {}`를 사용할 수 없으므로, 필요에 따라 docker 옵션 `--env`, `--env-file`, `--volume`을 사용하세요.

  ```json
  {
    "mcpServers": {
      "awslabs.aws-documentation-mcp-server": {
        "command": "docker",
        "args": [
          "run",
          "--rm",
          "--interactive",
          "--env",
          "FASTMCP_LOG_LEVEL=ERROR",
          "--env",
          "AWS_REGION=us-east-1",
          "--env-file",
          "/full/path/to/.env",
          "--volume",
          "/full/path/to/.aws:/app/.aws",
          "public.ecr.aws/awslabs-mcp/awslabs/aws-documentation-mcp-server:latest"
        ],
        "env": {}
      }
    }
  }
  ```

- 로컬 변경 사항을 테스트하려면 이미지를 빌드하고 태그를 지정할 수 있습니다. ECR 이미지 대신 이 태그를 사용하도록 MCP 구성을 변경해야 합니다.

  ```base
  cd src/aws-documentation-mcp-server
  docker build -t awslabs/aws-documentation-mcp-server .
  ```

### Kiro로 시작하기

<details>
<summary>Kiro에 설치</summary>

자세한 내용은 [Kiro IDE 문서](https://kiro.dev/docs/mcp/configuration/) 또는 [Kiro CLI 문서](https://kiro.dev/docs/cli/mcp/configuration/)를 참고하세요.

Kiro IDE에서:

1. `Kiro` > `MCP Servers`로 이동합니다.
2. `+ Add` 버튼을 클릭해 새 MCP 서버를 추가합니다.
3. 아래 구성을 붙여 넣습니다.

전역 구성은 `~/.kiro/settings/mcp.json`을, 프로젝트별 구성은 프로젝트 디렉터리의 `.kiro/settings/mcp.json`을 편집하세요.

#### `~/.kiro/settings/mcp.json`

macOS/Linux의 경우:

```json
{
  "mcpServers": {
    "awslabs-core-mcp-server": {
      "command": "uvx",
      "args": ["awslabs.core-mcp-server@latest"],
      "env": {
        "FASTMCP_LOG_LEVEL": "ERROR"
      }
    }
  }
}
```

Windows의 경우:

```json
{
  "mcpServers": {
    "awslabs-core-mcp-server": {
      "disabled": false,
      "timeout": 60,
      "type": "stdio",
      "command": "uv",
      "args": [
        "tool",
        "run",
        "--from",
        "awslabs.core-mcp-server@latest",
        "awslabs.core-mcp-server.exe"
      ],
      "env": {
        "FASTMCP_LOG_LEVEL": "ERROR"
      }
    }
  }
}
```

</details>

### Cline 및 Amazon Bedrock으로 시작하기

<details>
<summary>Cline 및 Amazon Bedrock으로 시작하기</summary>

**중요:** 아래 안내를 따르면 비용이 발생할 수 있으며 [Amazon Bedrock 요금](https://aws.amazon.com/bedrock/pricing/)이 적용됩니다. 관련 비용에 대한 책임은 사용자에게 있습니다. Cline 설정에서 원하는 모델을 선택하는 것 외에도, 선택한 모델(예: `anthropic.claude-3-7-sonnet`)이 Amazon Bedrock에서도 활성화되어 있는지 확인하세요. 자세한 내용은 Amazon Bedrock 파운데이션 모델(FM) 접근 활성화에 관한 [AWS 문서](https://docs.aws.amazon.com/bedrock/latest/userguide/model-access-modify.html)를 참고하세요.

1. 위의 **설치 및 설정** 섹션 절차에 따라 [Astral](https://docs.astral.sh/uv/getting-started/installation/)에서 `uv`를 설치하고, Python을 설치하고, 필요한 서비스에 대한 AWS 자격 증명을 구성합니다.

2. Visual Studio Code를 사용하는 경우 [Cline VS Code 확장](https://marketplace.visualstudio.com/items?itemName=saoudrizwan.claude-dev)(또는 사용 중인 IDE에 해당하는 확장)을 설치합니다. 설치 후 확장을 클릭해 엽니다. 안내가 표시되면 원하는 티어를 선택합니다. 여기서는 Amazon Bedrock을 사용하며 Cline API 대신 Amazon Bedrock API로 요청을 보내므로 Cline 무료 티어로도 충분합니다.

<p align="center">
  <img src="./docs/images/root-readme/install-cline-extension.png" width="800" height="400"  />
<p>

3. **MCP Servers** 버튼을 선택합니다.

<p align="center">
  <img src="./docs/images/root-readme/select-mcp-servers.png" width="500" height="800"  />
<p>

4. **Installed** 탭을 선택한 뒤 **Configure MCP Servers**를 클릭해 `cline_mcp_settings.json` 파일을 엽니다.

 <p align="center">
   <img src="./docs/images/root-readme/configure-mcp-servers.png" width="500" height="800"  />
 <p>

 5. `cline_mcp_settings.json` 파일의 `mcpServers` 객체에 사용할 MCP 서버를 추가합니다. 이 리포지토리에서 제공하는 일부 MCP 서버를 사용하는 아래 예시를 참고하세요. MCP 서버가 설치되도록 파일을 반드시 저장하세요.

#### `cline_mcp_settings.json`

macOS/Linux의 경우:

 ```json
 {
   "mcpServers": {
     "awslabs-core-mcp-server": {
       "command": "uvx",
       "args": ["awslabs.core-mcp-server@latest"],
       "env": {
         "FASTMCP_LOG_LEVEL": "ERROR",
         "MCP_SETTINGS_PATH": "path to your mcp settings file"
       }
     }
    }
  }
 ```

Windows의 경우:

```json
{
  "mcpServers": {
    "awslabs-core-mcp-server": {
      "disabled": false,
      "timeout": 60,
      "type": "stdio",
      "command": "uv",
      "args": [
        "tool",
        "run",
        "--from",
        "awslabs.core-mcp-server@latest",
        "awslabs.core-mcp-server.exe"
      ],
      "env": {
        "FASTMCP_LOG_LEVEL": "ERROR",
        "MCP_SETTINGS_PATH": "path to your mcp settings file"
      }
    }
  }
}
```

6. 설치가 완료되면 MCP Server Installed 탭에 MCP 서버 목록이 표시되고, 활성화되었음을 나타내는 녹색 슬라이더가 보입니다. 아래는 AWS용 MCP 서버 두 개를 사용한 예시입니다. 완료했으면 **Done**을 클릭합니다. 이제 Cline 채팅 인터페이스가 보일 것입니다.

<p align="center">
  <img src="./docs/images/root-readme/mcp-servers-installed.png" width="500" height="800"  />
<p>

<p align="center">
  <img src="./docs/images/root-readme/cline-chat-interface.png" width="500" height="800"  />
<p>

7. 기본적으로 API 제공자는 Cline으로 설정되어 있으며 무료 티어에는 제한이 있습니다. 다음으로 API 제공자를 AWS Bedrock으로 변경하여 Bedrock을 통해 LLM을 사용하고, 연결된 AWS 계정으로 과금되도록 설정합니다.

8. 설정 톱니바퀴를 클릭해 Cline 설정을 엽니다. **API Provider**에서 `Cline`을 `AWS Bedrock`으로 변경하고 인증 유형으로 `AWS Profile`을 선택합니다. 참고로 `AWS Credentials` 옵션도 동작하지만, 토큰 만료 시 자동으로 재발급되는 임시 자격 증명이 아니라 정적 자격 증명(액세스 키 ID와 비밀 액세스 키)을 사용합니다. 따라서 AWS Profile을 통한 임시 자격 증명이 더 안전하며 권장되는 방식입니다.

<p align="center">
  <img src="./docs/images/root-readme/cline-select-bedrock.png" width="500" height="800"  />
<p>

9. 사용할 기존 AWS 프로필을 기준으로 구성을 입력하고, 원하는 AWS 리전을 선택한 뒤 교차 리전 추론을 활성화합니다.

<p align="center">
  <img src="./docs/images/root-readme/cline-select-aws-profile.png" width="500" height="800"  />
<p>

<p align="center">
  <img src="./docs/images/root-readme/cline-api-provider-filled.png" width="500" height="800"  />
<p>

10. 다음으로 설정 페이지를 아래로 스크롤해 Custom Instructions 텍스트 박스를 찾습니다. 모든 프롬프트에서 `mcp-core` 서버를 시작점으로 사용하도록 아래 스니펫을 붙여 넣습니다:

```
For every new project, always look at your MCP servers and use mcp-core as the starting point every time. Also after a task completion include the list of MCP servers used in the operation.
```

<p align="center">
  <img src="./docs/images/root-readme/cline-custom-instructions.png" width="500" height="800"  />
<p>

11. 사용자 지정 프롬프트를 붙여 넣은 후 **Done**을 클릭해 채팅 인터페이스로 돌아갑니다.

12. 이제 질문을 시작하고 설치한 MCP 서버의 기능을 테스트할 수 있습니다. 채팅 인터페이스의 기본 옵션은 `Plan`으로, 사용자가 직접 조치를 취할 수 있도록 결과를 제시합니다(예: 파일에 복사해 붙여 넣을 샘플 구성 제공). 필요하면 `Act`로 전환해 Cline이 사용자를 대신해 작업을 수행하도록 할 수 있습니다(예: 웹 브라우저로 콘텐츠 검색, 리포지토리 복제, 코드 실행 등). "Auto-approve" 섹션을 켜면 제안을 승인하는 클릭을 생략할 수 있지만, 테스트 중에는 특히 Act가 선택된 경우 끄는 것을 권장합니다.

**참고:** 최적의 결과를 얻으려면 사용하려는 MCP 서버를 Cline에 명시적으로 지시하세요. 예: `Using the Terraform MCP Server, do...`
</details>

### Cursor로 시작하기

<details>
<summary>Cursor로 시작하기</summary>

1. 위의 **설치 및 설정** 섹션 절차에 따라 [Astral](https://docs.astral.sh/uv/getting-started/installation/)에서 `uv`를 설치하고, Python을 설치하고, 필요한 서비스에 대한 AWS 자격 증명을 구성합니다.

2. 사용 사례에 따라 MCP 구성을 두 위치 중 하나에 둘 수 있습니다:

  A. **프로젝트 구성**
    - 특정 프로젝트 전용 도구는 프로젝트 디렉터리에 `.cursor/mcp.json` 파일을 생성합니다.
    - 이렇게 하면 해당 프로젝트 내에서만 사용 가능한 MCP 서버를 정의할 수 있습니다.

  B. **전역 구성**
    - 모든 프로젝트에서 사용할 도구는 홈 디렉터리에 `~/.cursor/mcp.json` 파일을 생성합니다.
    - 이렇게 하면 모든 Cursor 워크스페이스에서 MCP 서버를 사용할 수 있습니다.

#### `.cursor/mcp.json`

macOS/Linux의 경우:

```json
 {
  "mcpServers": {
    "awslabs-core-mcp-server": {
      "command": "uvx",
      "args": ["awslabs.core-mcp-server@latest"],
      "env": {
        "FASTMCP_LOG_LEVEL": "ERROR"
      }
    }
  }
}
```

Windows의 경우:

```json
{
  "mcpServers": {
    "awslabs-core-mcp-server": {
      "disabled": false,
      "timeout": 60,
      "type": "stdio",
      "command": "uv",
      "args": [
        "tool",
        "run",
        "--from",
        "awslabs.core-mcp-server@latest",
        "awslabs.core-mcp-server.exe"
      ],
      "env": {
        "FASTMCP_LOG_LEVEL": "ERROR"
      }
    }
  }
}
```

3. **채팅에서 MCP 사용** Composer Agent는 MCP 설정 페이지의 Available Tools에 나열된 MCP 도구가 관련 있다고 판단되면 자동으로 사용합니다. 특정 도구를 의도적으로 사용하게 하려면 원하는 MCP 서버를 Cursor에 명시적으로 지시하세요. 예: `Using the Terraform MCP Server, do...`

4. **도구 승인** 기본적으로 Agent가 MCP 도구를 사용하려 할 때 승인을 요청하는 메시지가 표시됩니다. 도구 이름 옆의 화살표를 눌러 메시지를 확장하면 Agent가 어떤 인수로 도구를 호출하는지 확인할 수 있습니다.

</details>

### Windsurf로 시작하기

<details>
<summary>Windsurf로 시작하기</summary>

1. 위의 **설치 및 설정** 섹션 절차에 따라 [Astral](https://docs.astral.sh/uv/getting-started/installation/)에서 `uv`를 설치하고, Python을 설치하고, 필요한 서비스에 대한 AWS 자격 증명을 구성합니다.

2. **MCP 설정 접근**
   - Windsurf - Settings > Advanced Settings로 이동하거나 Command Palette > Open Windsurf Settings Page를 사용합니다.
   - "Model Context Protocol (MCP) Servers" 섹션을 찾습니다.

3. **MCP 서버 추가**
   - "Add Server"를 클릭해 새 MCP 서버를 추가합니다.
   - GitHub, Puppeteer, PostgreSQL 등 제공되는 템플릿에서 선택할 수 있습니다.
   - 또는 "Add custom server"를 클릭해 직접 서버를 구성할 수 있습니다.

4. **수동 구성**
   - `~/.codeium/windsurf/mcp_config.json`에 있는 MCP 구성 파일을 직접 편집할 수도 있습니다.

#### `~/.codeium/windsurf/mcp_config.json`

macOS/Linux의 경우:

 ```json
 {
   "mcpServers": {
     "awslabs-core-mcp-server": {
       "command": "uvx",
       "args": ["awslabs.core-mcp-server@latest"],
       "env": {
         "FASTMCP_LOG_LEVEL": "ERROR",
         "MCP_SETTINGS_PATH": "path to your mcp settings file"
       }
     }
    }
  }
 ```

Windows의 경우:

```json
{
  "mcpServers": {
    "awslabs-core-mcp-server": {
      "disabled": false,
      "timeout": 60,
      "type": "stdio",
      "command": "uv",
      "args": [
        "tool",
        "run",
        "--from",
        "awslabs.core-mcp-server@latest",
        "awslabs.core-mcp-server.exe"
      ],
      "env": {
        "FASTMCP_LOG_LEVEL": "ERROR",
        "MCP_SETTINGS_PATH": "path to your mcp settings file"
      }
    }
  }
}
```

</details>

### VS Code로 시작하기

<details>
<summary>VS Code에 설치</summary>

VS Code 설정 또는 `.vscode/mcp.json`에서 MCP 서버를 구성합니다(자세한 내용은 [VS Code MCP 문서](https://code.visualstudio.com/docs/copilot/chat/mcp-servers) 참고):

#### `.vscode/mcp.json`

macOS/Linux의 경우:

```json
{
  "mcpServers": {
    "awslabs-core-mcp-server": {
      "command": "uvx",
      "args": ["awslabs.core-mcp-server@latest"],
      "env": {
        "FASTMCP_LOG_LEVEL": "ERROR"
      }
    }
  }
}
```

Windows의 경우:

```json
{
  "mcpServers": {
    "awslabs-core-mcp-server": {
      "disabled": false,
      "timeout": 60,
      "type": "stdio",
      "command": "uv",
      "args": [
        "tool",
        "run",
        "--from",
        "awslabs.core-mcp-server@latest",
        "awslabs.core-mcp-server.exe"
      ],
      "env": {
        "FASTMCP_LOG_LEVEL": "ERROR"
      }
    }
  }
}
```
</details>

### Claude Code로 시작하기

<details>
<summary>Claude Code에 설치</summary>

CLI 또는 `.mcp.json`을 통해 Claude Code에서 MCP 서버를 구성합니다.

1. 위의 **설치 및 설정** 섹션 절차에 따라 [Astral](https://docs.astral.sh/uv/getting-started/installation/)에서 `uv`를 설치하고, Python을 설치하고, 필요한 서비스에 대한 AWS 자격 증명을 구성합니다.

2. **Claude Code CLI 명령 사용**

   MCP 서버를 추가하는 Claude Code CLI 명령:

   ```bash
   # 핵심 AWS 서비스 추가
   claude mcp add aws-api uvx awslabs.aws-api-mcp-server@latest
   claude mcp add aws-iac uvx awslabs.aws-iac-mcp-server@latest
   claude mcp add aws-docs uvx awslabs.aws-documentation-mcp-server@latest
   claude mcp add aws-support uvx awslabs.aws-support-mcp-server@latest
   claude mcp add aws-pricing uvx awslabs.aws-pricing-mcp-server@latest

   # AI/ML 및 Bedrock 서비스 추가
   claude mcp add bedrock-kb uvx awslabs.bedrock-kb-retrieval-mcp-server@latest

   # 데이터 및 분석 서비스 추가
   claude mcp add aws-dataprocessing uvx awslabs.aws-dataprocessing-mcp-server@latest
   claude mcp add aurora-dsql uvx awslabs.aurora-dsql-mcp-server@latest
   claude mcp add valkey uvx awslabs.valkey-mcp-server@latest

   # 설치된 서버 목록 조회
   claude mcp list
   ```

3. **수동 구성(대안)**

   프로젝트 루트에 `.mcp.json` 파일을 생성해 MCP 서버를 직접 구성할 수도 있습니다:

#### `.mcp.json`

macOS/Linux의 경우:

```json
{
  "mcpServers": {
    "awslabs.aws-iac-mcp-server": {
      "command": "uvx",
      "args": ["awslabs.aws-iac-mcp-server@latest"],
      "env": {
        "FASTMCP_LOG_LEVEL": "ERROR"
      }
    },
    "awslabs.aws-documentation-mcp-server": {
      "command": "uvx",
      "args": ["awslabs.aws-documentation-mcp-server@latest"],
      "env": {
        "FASTMCP_LOG_LEVEL": "ERROR",
        "AWS_DOCUMENTATION_PARTITION": "aws"
      }
    }
  }
}
```
</details>

## 샘플

AWS용 오픈 소스 MCP 서버를 바로 사용해 볼 수 있는 예제는 [samples](samples/) 디렉터리에 있습니다. 각 MCP 서버를 시작하는 데 도움이 되는 동작하는 코드와 단계별 가이드를 제공합니다.

## 바이브 코딩

이러한 MCP 서버를 AI 코딩 어시스턴트와 함께 사용해 [바이브 코딩](https://en.wikipedia.org/wiki/Vibe_coding)을 할 수 있습니다. 바이브 코딩 경험을 개선하는 팁과 요령은 [가이드](./VIBE_CODING_TIPS_TRICKS.md)를 참고하세요.

## 추가 리소스

- [Introducing AWS MCP Servers for code assistants](https://aws.amazon.com/blogs/machine-learning/introducing-aws-mcp-servers-for-code-assistants-part-1/)
- [Vibe coding with AWS MCP Servers | AWS Show & Tell](https://www.youtube.com/watch?v=qXGQQRMrcz0)
- [Supercharging AWS database development with AWS MCP servers](https://aws.amazon.com/blogs/database/supercharging-aws-database-development-with-aws-mcp-servers/)
- [AWS costs estimation using Amazon Q CLI and AWS Pricing MCP Server](https://aws.amazon.com/blogs/machine-learning/aws-costs-estimation-using-amazon-q-cli-and-aws-cost-analysis-mcp/)
- [Introducing AWS Serverless MCP Server: AI-powered development for modern applications](https://aws.amazon.com/blogs/compute/introducing-aws-serverless-mcp-server-ai-powered-development-for-modern-applications/)
- [Announcing new Model Context Protocol (MCP) Servers for AWS Serverless and Containers](https://aws.amazon.com/about-aws/whats-new/2025/05/new-model-context-protocol-servers-aws-serverless-containers/)
- [Accelerating application development with the Amazon EKS MCP server](https://aws.amazon.com/blogs/containers/accelerating-application-development-with-the-amazon-eks-model-context-protocol-server/)
- [Amazon Neptune announces MCP (Model Context Protocol) Server](https://aws.amazon.com/about-aws/whats-new/2025/05/amazon-neptune-mcp-server/)
- [Terraform MCP Server Vibe Coding](https://youtu.be/i2nBD65md0Y)
- [How to Generate AWS Architecture Diagrams Using Amazon Q CLI and MCP](https://community.aws/content/2vPiiPiBSdRalaEax2rVDtshpf3/how-to-generate-aws-architecture-diagrams-using-amazon-q-cli-and-mcp)
- [Harness the power of MCP servers with Amazon Bedrock Agents](https://aws.amazon.com/blogs/machine-learning/harness-the-power-of-mcp-servers-with-amazon-bedrock-agents/)
- [Unlocking the power of Model Context Protocol (MCP) on AWS](https://aws.amazon.com/blogs/machine-learning/unlocking-the-power-of-model-context-protocol-mcp-on-aws/)
- [AWS Price List Gets a Natural Language Upgrade: Introducing the AWS Pricing MCP Server](https://aws.amazon.com/blogs/aws-cloud-financial-management/aws-price-list-gets-a-natural-language-upgrade-introducing-the-aws-pricing-mcp-server/)
- [AWS SheBuilds: AWS Team's Journey from Internal Tools to Open Source AI Infrastructure](https://www.youtube.com/watch?v=DZFgufNCvAo)
- [Guidance for Vibe Coding with AWS MCP servers](https://aws.amazon.com/solutions/guidance/vibe-coding-with-aws-mcp-servers/)
- [Vibe coding with AWS MCP Servers | Hands-on Workshop](https://github.com/aws-solutions-library-samples/guidance-for-vibe-coding-with-aws-mcp-servers)

## 보안

자세한 내용은 [CONTRIBUTING](CONTRIBUTING.md#security-issue-notifications)을 참고하세요.

## 기여하기

멋진 기여자 여러분께 큰 감사를 전합니다! 이 프로젝트를 더 좋게 만들어 주셔서 고맙습니다!

[![contributors](https://contrib.rocks/image?repo=awslabs/mcp&max=2000)](https://github.com/awslabs/mcp/graphs/contributors)

어떤 형태의 기여든 환영합니다! 자세한 내용은 [기여자 가이드](CONTRIBUTING.md)를 확인하세요.

## 개발자 가이드

라이브러리에 새 MCP 서버를 추가하려면 [개발 가이드](DEVELOPER_GUIDE.md)를 확인하고 [설계 가이드라인](DESIGN_GUIDELINES.md)을 반드시 따라 주세요.

## 라이선스

이 프로젝트는 Apache-2.0 라이선스로 배포됩니다.

## 면책 조항

MCP 서버를 사용하기 전에, 해당 사용이 귀사의 고유한 보안 및 품질 관리 관행과 표준은 물론 귀사와 귀사의 콘텐츠에 적용되는 법률, 규칙, 규정을 준수하는지 확인하기 위해 독립적인 평가를 수행하는 것을 고려하시기 바랍니다.
