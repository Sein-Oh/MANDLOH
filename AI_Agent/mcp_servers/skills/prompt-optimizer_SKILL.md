---
name: prompt-optimizer
description: 사용자의 모호하거나 단순한 프롬프트를 고성능 LLM이 최상의 성능을 발휘할 수 있도록 구조화된 프롬프트 템플릿으로 발전시키고 즉시 실행합니다.
category: Prompt Engineering
triggers:
  - 프롬프트 개선
  - 프롬프트 최적화
  - 프롬프트 엔지니어링
  - 프롬프트 작성
  - 프롬프트 짜줘
  - 프롬프트 생성
  - 프롬프트 다듬기
  - LLM 프롬프트
  - 프롬프트 템플릿
---

# Prompt Optimizer Skill

## 개요
사용자의 초기 프롬프트를 분석하여 역할(Role), 맥락(Context), 제약조건(Constraints), 출력 형식(Output Format)을 갖춘 고품질 구조화 프롬프트로 최적화합니다.

## 실행 지침 (Instructions)
1. **프롬프트 구조화 프레임워크**:
   - **Role (역할)**: 대상 도메인의 최고 전문가 페르소나 부여
   - **Context & Goal (맥락 및 목표)**: 명확한 배경 설명과 핵심 목표
   - **Constraints (제약조건)**: 준수해야 할 어조, 분량, 제외 사항
   - **Output Format (출력 형식)**: 마크다운, 표, JSON 등 구체적인 포맷 지정
   - **Variables**: 동적 입력값은 `{{VARIABLE_NAME}}` 형태로 명시
2. **필수 연쇄 실행 (Mandatory 2-Step Execution)**:
   - **1단계 [최적화된 프롬프트 템플릿]**: 복사하여 재사용할 수 있는 고품질 프롬프트 제공
   - **2단계 [즉시 실행 결과물]**: 최적화된 프롬프트에 사용자의 입력값을 적용하여 실제 도출된 최종 결과물을 즉시 작성하여 제공

---
⚡ **[AI 어시스턴트 지침]**: 답변을 작성할 때 반드시 최상단 첫 줄에 `### 🎯 [적용 스킬: prompt-optimizer]` 말머리를 붙이고 위 지침에 따라 최종 답변을 완성하십시오.
