---
name: prompt-optimizer
description: 사용자의 모호하거나 단순한 프롬프트를 고성능 LLM이 최적의 답변을 낼 수 있는 체계적인 프롬프트로 발전시킵니다.
category: Prompt Engineering
triggers:
  - 프롬프트 개선
  - 프롬프트 최적화
  - 프롬프트 엔지니어링
---

# Prompt Optimizer Skill

## 개요
사용자의 초기 프롬프트를 분석하여 역할(Role), 맥락(Context), 제약조건(Constraints), 출력 형식(Output Format)을 갖춘 고품질 구조화 프롬프트로 최적화합니다.

## 실행 지침 (Instructions)
1. 사용자의 핵심 목표와 타겟 독자(또는 LLM 모델 특성)를 명확히 식별합니다.
2. 역할(Role), 맥락(Context), 제약조건(Constraints), 구체적인 출력 형식(Output Format)을 체계적으로 구조화합니다.
3. Few-shot 예시나 단계별 생각(Chain-of-Thought) 유도가 필요한 경우 적절한 가이드를 포함합니다.
4. LLM이 일관되게 고품질 결과를 출력할 수 있도록 완성형 최종 프롬프트 템플릿을 생성합니다.
5. **[필수 연쇄 실행 (2-Step Execution)]**: 프롬프트 템플릿만 출력하고 멈추지 마십시오. 반드시 최적화된 프롬프트를 즉시 실행하여 도출된 **'실제 최종 결과물(Final Answer)'**까지 한 번의 답변에서 이어서 완성하여 제공하십시오.
