import pymysql
import streamlit as st
from openai import OpenAI
import os
import json
from dotenv import load_dotenv
from datetime import datetime

# 환경 변수 로드
load_dotenv()
OPENAI_API_KEY = st.secrets["OPENAI_API_KEY"]
MODEL = 'gpt-4o'

# OpenAI API 설정
client = OpenAI(api_key=OPENAI_API_KEY)

# 초기 프롬프트
initial_prompt = (
    "당신은 중학생의 자유 탐구를 돕는 챗봇이며, 이름은 '과학탐구 도우미'입니다."
    "이 탐구는 중학교 1학년 학생들이 하는 탐구이므로, 중학교 1학년 수준에 맞게 설명해야 합니다."
    "탐구 주제는 '종이, 고무줄, 빨대, 풍선, 책, 실, 페트병, 캔, 종이컵 등 일상에서 쉽게 접할 수 있는 물건들로 할 수 있는 실험'입니다."
    "과학 개념을 설명할 때는 14세 정도의 학생 수준으로 간결하게 설명하세요."
    "학생에게는 다음과 같은 절차로 챗봇을 활용하도록 안내되었습니다: ① 먼저 인공지능에게 탐구 주제를 알려주고, 탐구에 대해 궁금한 것을 물어보세요. ② 궁금한 것을 다 물어봤다면, 인공지능에게 '궁금한 건 다 물어봤어'라고 말해주세요. ③ 그러면 인공지능이 당신의 생각을 물어볼 거예요. 당신이 생각한 '실험 가설'과 '실험 방법'을 인공지능에게 알려주세요. ④ 인공지능이 당신의 생각에 대해 추가 질문을 하면, 그것을 고민해 답해보세요. 궁금한 게 있으면 인공지능에게 물어봐도 돼요. ⑤ 충분히 대화가 이루어지면 인공지능이 [다음] 버튼을 눌러도 된다고 알려줘요. 인공지능이 [다음] 버튼을 누르라고 했을 때 버튼을 누르세요!"
    "대화 시작 단계에서 학생이 탐구 주제를 말하지 않는다면, 탐구 주제가 무엇인지 먼저 물어보세요."
    "학생에게 탐구를 안내하는 것은 두 단계로 진행됩니다. 1단계는 학생이 탐구와 관련해 궁금한 점을 질문하는 단계입니다. 2단계는 학생의 가설과 실험 과정에 대해 당신이 학생에게 질문하며 실험을 정교화하는 단계입니다."
    "1단계에서는 학생이 제시하는 질문에 답하면서, 그와 동시에 학생의 수준과 특성을 진단하세요. 예를 들어 학생이 탐구의 변인, 준비물, 관련 지식 등 세부 사항까지 세세하게 질문하는 학생인지, 또는 탐구의 가설과 과정에 대해서만 질문하는 학생인지, 또는 적절한 질문을 잘 하지 못하는 학생인지 등을 판단하세요."
    "학생이 궁금한 것을 다 물어봤다고 하거나, 더이상 질문이 없다고 한다면, 이제 학생이 생각한 실험 가설과 실험 과정을 써달라고 요청하세요. 이때 학생이 실험 가설과 실험 과정을 모르겠다고 하더라도, 절대 알려줘서는 안 됩니다. 간단하게라도 써 보도록 유도하세요."
    "학생이 생각한 실험 가설과 과정을 쓰고 나면, 그것을 정교화하는 2단계로 넘어갑니다. 1단계에서 학생 수준과 특성을 진단한 결과를 바탕으로, 학생의 실험 가설과 과정에 대해 질문하며 정교화하세요. 예를 들어 탐구의 변인이나 준비물 등 세부 사항까지 질문하는 학생이라면 가설과 실험 과정에 대해 더 깊이 있는 논의가 이루어지도록 질문하고, 탐구의 가설과 과정에 대해서만 질문하는 학생이라면 변인이나 준비물 등의 세부 사항을 질문하고, 적절한 질문을 잘 하지 못한 학생이라면 변인 인식, 가설 설정, 실험 설계 등 탐구의 전반적인 과정을 질문을 통해 안내하세요."
    "2단계에서는 최소 5번 이상 대화가 오가도록 하세요."
    "탐구의 변인, 가설, 과정에 관한 충분한 논의가 이루어지면, 학생에게 [다음] 버튼을 눌러 다음 단계로 진행하라고 이야기하세요. 단, [다음] 버튼은 필요한 논의가 모두 끝난 후에 눌러야 합니다. 그 전에는 [다음] 버튼을 누르지 말라고 안내하세요."
    "[다음] 버튼은 다음 세 가지 조건이 모두 충족됐을 때 누를 수 있습니다: ① 학생 수준과 특성이 진단되었다. ② 학생이 스스로 생각한 실험 가설과 과정을 제시했다. ③ 2단계에서 5회 이상 대화가 오갔다. 이 조건이 충족되지 않았다면, 절대로 [다음] 버튼을 누르라고 하면 안 됩니다."
    "한 번에 여러 질문을 하면 학생이 혼란스러워 할 수 있으니, 한 번에 하나의 질문만 하세요."
    "반드시 한 번 이상 학생이 직접 실험 가설과 과정을 작성하도록 요청하세요."
    "어떤 상황에서든 절대로 실험 가설이나 실험 과정을 직접적으로 알려줘서는 안 됩니다. 당신이 할 일은 학생이 스스로 사고하여 실험 가설과 과정을 작성하도록 유도하는 것입니다."
    "학생이 실험 가설이나 과정을 모르겠다거나 못 쓰겠다고 하더라도 절대 알려주지 마세요. 간단하게라도 써 보도록 유도하세요."
    "당신의 역할은 정답을 알려주는 게 아니라, 학생이 사고하며 탐구를 설계하도록 교육적 지원을 하는 것입니다."
)

# MySQL 저장 함수
def save_to_db():
    number = st.session_state.get('user_number', '').strip()
    name = st.session_state.get('user_name', '').strip()

    if not number or not name:  # 학번과 이름 확인
        st.error("사용자 학번과 이름을 입력해야 합니다.")
        return False  # 저장 실패

    try:
        db = pymysql.connect(
            host=st.secrets["DB_HOST"],
            user=st.secrets["DB_USER"],
            password=st.secrets["DB_PASSWORD"],
            database=st.secrets["DB_DATABASE"],
            charset="utf8mb4",  # UTF-8 지원
            autocommit=True  # 자동 커밋 활성화
        )
        cursor = db.cursor()
        now = datetime.now()

        sql = """
        INSERT INTO qna (number, name, chat, time)
        VALUES (%s, %s, %s, %s)
        """
        chat = json.dumps(st.session_state["messages"], ensure_ascii=False)  # 대화 내용을 JSON 문자열로 변환
        val = (number, name, chat, now)

        # SQL 실행
        cursor.execute(sql, val)
        cursor.close()
        db.close()
        st.success("대화 내용 처리 중입니다.")
        return True  # 저장 성공
    except pymysql.MySQLError as db_err:
        st.error(f"DB 처리 중 오류가 발생했습니다: {db_err}")
        return False  # 저장 실패
    except Exception as e:
        st.error(f"알 수 없는 오류가 발생했습니다: {e}")
        return False  # 저장 실패

# GPT 응답 생성 함수
def get_chatgpt_response(prompt):
    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "system", "content": initial_prompt}] + st.session_state["messages"] + [{"role": "user", "content": prompt}],
    )
    answer = response.choices[0].message.content

    # 사용자와 챗봇 대화만 기록
    st.session_state["messages"].append({"role": "user", "content": prompt})
    st.session_state["messages"].append({"role": "assistant", "content": answer})
    return answer

# 페이지 1: 학번 및 이름 입력
def page_1():
    st.title("보라중학교 탐구 도우미 챗봇")
    st.write("학번과 이름을 입력한 뒤 '다음' 버튼을 눌러주세요.")

    if "user_number" not in st.session_state:
        st.session_state["user_number"] = ""
    if "user_name" not in st.session_state:
        st.session_state["user_name"] = ""

    st.session_state["user_number"] = st.text_input("학번", value=st.session_state["user_number"])
    st.session_state["user_name"] = st.text_input("이름", value=st.session_state["user_name"])

    st.write(" ")  # Add space to position the button at the bottom properly
    if st.button("다음", key="page1_next_button"):
        if st.session_state["user_number"].strip() == "" or st.session_state["user_name"].strip() == "":
            st.error("학번과 이름을 모두 입력해주세요.")
        else:
            st.session_state["step"] = 2
            st.rerun()

# 페이지 2: 사용법 안내
def page_2():
    st.title("탐구 도우미 활용 방법")
    st.write(
        """  
        ※주의! '자동 번역'을 활성화하면 대화가 이상하게 번역되므로 활성화하면 안 돼요. 혹시 이미 '자동 번역' 버튼을 눌렀다면 비활성화 하세요.  

        ① 먼저 탐구에 대해 궁금한 것을 인공지능에게 물어보세요.  

        ② 궁금한 것을 다 물어봤다면, 인공지능에게 '궁금한 건 다 물어봤어'라고 말해주세요.  

        ③ 그러면 인공지능이 당신의 생각을 물어볼 거예요. 당신이 생각한 '실험 가설'과 '실험 방법'을 인공지능에게 알려주세요.  

        ④ 인공지능이 당신의 생각에 대해 추가 질문을 하면, 그것을 고민해 답해보세요. 궁금한 게 있으면 인공지능에게 물어봐도 돼요.  

        ⑤ 충분히 대화가 이루어지면 인공지능이 [다음] 버튼을 눌러도 된다고 알려줘요. 인공지능이 [다음] 버튼을 누르라고 했을 때 버튼을 누르세요!  

        위 내용을 충분히 숙지했다면, 아래의 [다음] 버튼을 눌러 진행해주세요.  
        """
    )

    st.write(" ")  # Add space to position the button at the bottom properly
    if st.button("다음", key="page2_next_button"):
        st.session_state["step"] = 3
        st.rerun()

# 페이지 3: GPT와 대화
def page_3():
    st.title("탐구 도우미 활용하기")
    st.write("탐구 도우미와 대화를 나누며 탐구를 설계하세요.")

    # 학번과 이름 확인
    if not st.session_state.get("user_number") or not st.session_state.get("user_name"):
        st.error("학번과 이름이 누락되었습니다. 다시 입력해주세요.")
        st.session_state["step"] = 1
        st.rerun()

    # 대화 기록 초기화
    if "messages" not in st.session_state:
        st.session_state["messages"] = []

    if "user_input_temp" not in st.session_state:
        st.session_state["user_input_temp"] = ""

    if "recent_message" not in st.session_state:
        st.session_state["recent_message"] = {"user": "", "assistant": ""}

    # 대화 UI
    user_input = st.text_area(
        "You: ",
        value=st.session_state["user_input_temp"],
        key="user_input",
        on_change=lambda: st.session_state.update({"user_input_temp": st.session_state["user_input"]}),
    )

    if st.button("전송") and user_input.strip():
        # GPT 응답 가져오기
        assistant_response = get_chatgpt_response(user_input)

        # 최근 대화 저장
        st.session_state["recent_message"] = {"user": user_input, "assistant": assistant_response}

        # 사용자 입력을 초기화하고 페이지를 새로고침
        st.session_state["user_input_temp"] = ""
        st.rerun()

    # 최근 대화 출력
    st.subheader("📌 최근 대화")
    if st.session_state["recent_message"]["user"] or st.session_state["recent_message"]["assistant"]:
        st.write(f"**You:** {st.session_state['recent_message']['user']}")
        st.write(f"**과학탐구 도우미:** {st.session_state['recent_message']['assistant']}")
    else:
        st.write("아직 최근 대화가 없습니다.")

    # 다음 버튼 (저장 로직 제거)
    st.write(" ")  # Add space to position the button at the bottom properly
    if st.button("다음", key="page3_next_button"):
        st.session_state["step"] = 4
        st.rerun()

    # 누적 대화 출력
    st.subheader("📜 누적 대화 목록")
    if st.session_state["messages"]:
        for message in st.session_state["messages"]:
            if message["role"] == "user":
                st.write(f"**You:** {message['content']}")
            elif message["role"] == "assistant":
                st.write(f"**과학탐구 도우미:** {message['content']}")
    else:
        st.write("아직 대화 기록이 없습니다.")

# 피드백 저장 함수
def save_feedback_to_db(feedback):
    number = st.session_state.get('user_number', '').strip()
    name = st.session_state.get('user_name', '').strip()

    if not number or not name:  # 학번과 이름 확인
        st.error("사용자 학번과 이름을 입력해야 합니다.")
        return False  # 저장 실패

    try:
        db = pymysql.connect(
            host=st.secrets["DB_HOST"],
            user=st.secrets["DB_USER"],
            password=st.secrets["DB_PASSWORD"],
            database=st.secrets["DB_DATABASE"],
            charset="utf8mb4",  # UTF-8 지원
            autocommit=True  # 자동 커밋 활성화
        )
        cursor = db.cursor()
        now = datetime.now()

        sql = """
        INSERT INTO feedback (number, name, feedback, time)
        VALUES (%s, %s, %s, %s)
        """
        val = (number, name, feedback, now)

        # SQL 실행
        cursor.execute(sql, val)
        cursor.close()
        db.close()
        st.success("피드백이 성공적으로 저장되었습니다.")
        return True  # 저장 성공
    except pymysql.MySQLError as db_err:
        st.error(f"DB 처리 중 오류가 발생했습니다: {db_err}")
        return False  # 저장 실패
    except Exception as e:
        st.error(f"알 수 없는 오류가 발생했습니다: {e}")
        return False  # 저장 실패

# 페이지 4: 실험 과정 출력
def page_4():
    st.title("탐구 도우미의 제안")
    st.write("탐구 도우미가 대화 내용을 정리 중입니다. 잠시만 기다려주세요.")

    # 피드백 생성 및 대화에 추가
    if "experiment_plan" not in st.session_state:
        # 대화 히스토리 정리
        chat_history = "\n".join(
            f"{msg['role']}: {msg['content']}" for msg in st.session_state["messages"]
        )
        prompt = f"다음은 학생과 과학탐구 도우미의 대화 기록입니다:\n{chat_history}\n\n"
        prompt += "위 대화를 바탕으로, 다음 내용을 포함해 탐구 내용과 피드백을 작성하세요: 1. 대화 내용을 종합해 도출한 탐구 가설 및 과정, 2. 학생이 제시한 탐구 가설 및 과정에서 수정한 부분과 수정한 이유, 3. 학생의 탐구 능력에 관한 피드백(강점과 개선점 등)."

        # OpenAI API 호출
        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "system", "content": prompt}]
        )
        st.session_state["experiment_plan"] = response.choices[0].message.content

        # 피드백을 대화 히스토리에 추가
        st.session_state["messages"].append({"role": "assistant", "content": st.session_state["experiment_plan"]})

    # 중복 저장 방지: 피드백 저장 여부 확인
    if "feedback_saved" not in st.session_state:
        st.session_state["feedback_saved"] = False  # 초기화

    if not st.session_state["feedback_saved"]:
        if save_to_db():  # 기존 save_to_db 함수 재활용
            st.session_state["feedback_saved"] = True  # 저장 성공 시 플래그 설정
            st.success("대화와 피드백이 성공적으로 저장되었습니다.")
        else:
            st.error("저장에 실패했습니다. 다시 시도해주세요.")

    # 피드백 출력
    st.subheader("📋 생성된 피드백")
    st.write(st.session_state["experiment_plan"])

# 메인 로직
if "step" not in st.session_state:
    st.session_state["step"] = 1

if st.session_state["step"] == 1:
    page_1()
elif st.session_state["step"] == 2:
    page_2()
elif st.session_state["step"] == 3:
    page_3()
elif st.session_state["step"] == 4:
    page_4()