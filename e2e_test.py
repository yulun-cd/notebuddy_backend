#!/usr/bin/env python3
"""
End-to-End Workflow Test for NoteBuddy Backend API
This script tests the complete workflow in a single sequential test.
"""

import os
import sys
import subprocess
import time
import requests
import json
from datetime import datetime
from pathlib import Path

# Set environment to test before importing anything
os.environ["ENVIRONMENT"] = "test"

# Base URL for the API
BASE_URL = "http://localhost:8001"


class EndToEndWorkflowTest:
    def __init__(self):
        self.token = None
        self.refresh_token = None
        self.user_data = {
            "email": f"e2e_test_{int(time.time())}@example.com",
            "password": "e2e_test_password_123",
        }
        self.main_transcript_id = None
        self.test_transcript_id = None
        self.note_id = None
        self.server_process = None
        self.workflow_steps = []
        self.workflow_content = {}

    def log_step(self, step_name, status, details=""):
        """Log workflow step result"""
        step = {
            "step_name": step_name,
            "status": status,
            "details": details,
            "timestamp": datetime.now().isoformat(),
        }
        self.workflow_steps.append(step)

        status_icon = "✅" if status == "PASSED" else "❌"
        print(f"{status_icon} {step_name} - {status}")
        if details:
            print(f"   📝 {details}")

    def get_headers(self):
        """Get headers with authentication token"""
        if self.token:
            return {
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json",
            }
        return {"Content-Type": "application/json"}

    def start_test_server(self):
        """Start the test server with test database"""
        self.log_step(
            "Start Test Server", "STARTING", "Starting test server on port 8001"
        )

        # Set environment for test server
        env = os.environ.copy()
        env["ENVIRONMENT"] = "test"

        # Start the server in a subprocess
        self.server_process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "app.main:app",
                "--host",
                "0.0.0.0",
                "--port",
                "8001",
            ],
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        # Wait for server to start
        time.sleep(5)

        # Verify server is running
        try:
            response = requests.get(f"{BASE_URL}/health", timeout=5)
            if response.status_code == 200:
                self.log_step(
                    "Start Test Server",
                    "PASSED",
                    "Server started successfully on port 8001",
                )
                return True
            else:
                self.log_step(
                    "Start Test Server",
                    "FAILED",
                    f"Health check failed: {response.status_code}",
                )
                return False
        except Exception as e:
            self.log_step(
                "Start Test Server", "FAILED", f"Server failed to start: {str(e)}"
            )
            return False

    def stop_test_server(self):
        """Stop the test server"""
        if self.server_process:
            self.server_process.terminate()
            self.server_process.wait()
            self.log_step("Stop Test Server", "COMPLETED", "Test server stopped")

    def cleanup_test_database(self):
        """Clean up the test database file"""
        test_db_path = "test_notebuddy.db"
        if os.path.exists(test_db_path):
            os.remove(test_db_path)
            self.log_step("Cleanup Database", "COMPLETED", "Test database cleaned up")

    def test_workflow(self):
        """Single workflow test following the specified sequence"""
        try:
            # ===== STEP 1: User Registration and Login =====
            self.log_step("Step 1", "STARTING", "User registration and login")

            # User registration
            response = requests.post(
                f"{BASE_URL}/auth/register", json=self.user_data, timeout=10
            )
            if response.status_code != 200:
                self.log_step(
                    "Step 1", "FAILED", f"Registration failed: {response.text}"
                )
                return False

            # User login
            response = requests.post(
                f"{BASE_URL}/auth/login",
                json={
                    "email": self.user_data["email"],
                    "password": self.user_data["password"],
                },
                timeout=10,
            )
            if response.status_code == 200:
                data = response.json()
                self.token = data["access_token"]
                self.refresh_token = data["refresh_token"]
                self.log_step(
                    "Step 1", "PASSED", "User registered and logged in successfully"
                )
            else:
                self.log_step("Step 1", "FAILED", f"Login failed: {response.text}")
                return False

            # ===== STEP 2: Transcript Operations =====
            self.log_step("Step 2", "STARTING", "Transcript operations")

            # Create main transcript with specified text
            transcript_content = """这座城市总有一种力量，把人吸引进来，有时候是因为机会，有时候只是因为它能给人一种匿名的自由。走在街上，你会注意到层层叠叠的痕迹：斑驳的红砖外墙上还留着褪色的招牌，玻璃幕墙高楼映着天空，被撕去一半的海报重叠在一起，像过去事件的残影。人群的流动也有节奏，不只是通勤者急促的脚步，还有那些似乎故意放慢、不愿被催促的人。车喇叭、公交车刹车声、偶然听见的对话片段混在一起，你会发现这并不是纯粹的嘈杂，更像是一场管弦乐排练，每个人都在演奏自己的部分，却隐约在为某种更大的合奏做准备。\n然后是那些安静的角落：一间咖啡馆，旧瓷杯口有细小的裂痕，店员会在收据上给常客写字条；一个小公园，长椅上总有同一个老人喂鸽子；一条狭窄的巷子，只有每天早晨十分钟能见到阳光，但几盆破旧花盆里的植物依然顽强地生长。你会觉得这座城市并不是单纯建造出来的，而是一直在被人们协商、被时间塑造，在路过者和停留者之间，在记忆和变化之间，在历史的重量与明天的躁动之间，不断地摇摆与生成。"""

            transcript_data = {
                "title": "端到端测试",
                "content": transcript_content,
            }
            response = requests.post(
                f"{BASE_URL}/transcripts/",
                json=transcript_data,
                headers=self.get_headers(),
                timeout=10,
            )
            if response.status_code == 200:
                transcript = response.json()
                self.main_transcript_id = transcript["id"]
                self.workflow_content["original_transcript"] = transcript_content
                self.log_step(
                    "Step 2a",
                    "PASSED",
                    f"Main transcript created with ID: {self.main_transcript_id}",
                )
            else:
                self.log_step(
                    "Step 2a", "FAILED", f"Transcript creation failed: {response.text}"
                )
                return False

            # Get transcript by ID
            response = requests.get(
                f"{BASE_URL}/transcripts/{self.main_transcript_id}",
                headers=self.get_headers(),
                timeout=10,
            )
            if response.status_code == 200:
                retrieved_transcript = response.json()
                assert (
                    retrieved_transcript["id"] == self.main_transcript_id
                ), "Transcript ID mismatch"
                assert (
                    retrieved_transcript["content"] == transcript_content
                ), "Transcript content mismatch"
                self.log_step(
                    "Step 2b", "PASSED", "Transcript retrieved successfully by ID"
                )
            else:
                self.log_step(
                    "Step 2b", "FAILED", f"Transcript retrieval failed: {response.text}"
                )
                return False

            # Get all transcripts
            response = requests.get(
                f"{BASE_URL}/transcripts/", headers=self.get_headers(), timeout=10
            )
            if response.status_code == 200:
                transcripts = response.json()
                assert isinstance(transcripts, list), "Transcripts should be a list"
                assert len(transcripts) > 0, "Should have at least one transcript"
                self.log_step(
                    "Step 2c", "PASSED", f"Retrieved {len(transcripts)} transcripts"
                )
            else:
                self.log_step(
                    "Step 2c",
                    "FAILED",
                    f"Transcripts retrieval failed: {response.text}",
                )
                return False

            # Update transcript by adding "【更新】" prefix
            updated_content = "【更新】" + transcript_content
            update_data = {
                "title": "Updated Transcript",
                "content": updated_content,
            }
            response = requests.put(
                f"{BASE_URL}/transcripts/{self.main_transcript_id}",
                json=update_data,
                headers=self.get_headers(),
                timeout=10,
            )
            if response.status_code == 200:
                updated_transcript = response.json()
                assert (
                    updated_transcript["content"] == updated_content
                ), "Transcript content not updated correctly"
                self.workflow_content["updated_transcript"] = updated_content
                self.log_step(
                    "Step 2d", "PASSED", "Transcript updated with 【更新】 prefix"
                )
            else:
                self.log_step(
                    "Step 2d", "FAILED", f"Transcript update failed: {response.text}"
                )
                return False

            # Create a test transcript and delete it
            test_transcript_data = {
                "title": "Test Transcript for Deletion",
                "content": "This is a test transcript that will be deleted.",
            }
            response = requests.post(
                f"{BASE_URL}/transcripts/",
                json=test_transcript_data,
                headers=self.get_headers(),
                timeout=10,
            )
            if response.status_code == 200:
                test_transcript = response.json()
                self.test_transcript_id = test_transcript["id"]
                self.log_step(
                    "Step 2e",
                    "PASSED",
                    f"Test transcript created with ID: {self.test_transcript_id}",
                )

                # Delete the test transcript
                response = requests.delete(
                    f"{BASE_URL}/transcripts/{self.test_transcript_id}",
                    headers=self.get_headers(),
                    timeout=10,
                )
                if response.status_code == 200:
                    # Verify deletion
                    response_get = requests.get(
                        f"{BASE_URL}/transcripts/{self.test_transcript_id}",
                        headers=self.get_headers(),
                        timeout=10,
                    )
                    assert (
                        response_get.status_code == 404
                    ), "Test transcript should not exist after deletion"
                    self.log_step(
                        "Step 2f",
                        "PASSED",
                        "Test transcript created and deleted successfully",
                    )
                else:
                    self.log_step(
                        "Step 2f",
                        "FAILED",
                        f"Test transcript deletion failed: {response.text}",
                    )
                    return False
            else:
                self.log_step(
                    "Step 2e",
                    "FAILED",
                    f"Test transcript creation failed: {response.text}",
                )
                return False

            self.log_step("Step 2", "PASSED", "All transcript operations completed")

            # ===== STEP 3: Note Generation =====
            self.log_step("Step 3", "STARTING", "Note generation (no timeout allowed)")

            # Generate note for the remaining transcript
            response = requests.post(
                f"{BASE_URL}/transcripts/{self.main_transcript_id}/generate-note",
                headers=self.get_headers(),
                timeout=60,  # Longer timeout but no fallback
            )
            if response.status_code == 200:
                note_data = response.json()
                self.note_id = note_data["note"]["id"]
                self.workflow_content["generated_note"] = note_data["note"]["content"]
                self.log_step(
                    "Step 3", "PASSED", f"Note generated with ID: {self.note_id}"
                )
            else:
                self.log_step(
                    "Step 3", "FAILED", f"Note generation failed: {response.text}"
                )
                return False

            # ===== STEP 4: Note Operations (same workflow as transcript) =====
            self.log_step("Step 4", "STARTING", "Note operations")

            # Get note by ID
            response = requests.get(
                f"{BASE_URL}/notes/{self.note_id}",
                headers=self.get_headers(),
                timeout=10,
            )
            if response.status_code == 200:
                retrieved_note = response.json()
                assert retrieved_note["id"] == self.note_id, "Note ID mismatch"
                self.log_step("Step 4a", "PASSED", "Note retrieved successfully by ID")
            else:
                self.log_step(
                    "Step 4a", "FAILED", f"Note retrieval failed: {response.text}"
                )
                return False

            # Get all notes
            response = requests.get(
                f"{BASE_URL}/notes/", headers=self.get_headers(), timeout=10
            )
            if response.status_code == 200:
                notes = response.json()
                assert isinstance(notes, list), "Notes should be a list"
                assert len(notes) > 0, "Should have at least one note"
                self.log_step("Step 4b", "PASSED", f"Retrieved {len(notes)} notes")
            else:
                self.log_step(
                    "Step 4b", "FAILED", f"Notes retrieval failed: {response.text}"
                )
                return False

            # Update note
            update_note_data = {
                "title": "Updated Note",
                "content": "This note has been updated as part of the workflow test.",
            }
            response = requests.put(
                f"{BASE_URL}/notes/{self.note_id}",
                json=update_note_data,
                headers=self.get_headers(),
                timeout=10,
            )
            if response.status_code == 200:
                updated_note = response.json()
                assert (
                    updated_note["content"] == update_note_data["content"]
                ), "Note content not updated correctly"
                self.log_step("Step 4c", "PASSED", "Note updated successfully")
            else:
                self.log_step(
                    "Step 4c", "FAILED", f"Note update failed: {response.text}"
                )
                return False

            self.log_step("Step 4", "PASSED", "All note operations completed")

            # ===== STEP 5: Question Generation =====
            self.log_step("Step 5", "STARTING", "Question generation")

            # Generate questions for the note
            response = requests.post(
                f"{BASE_URL}/notes/{self.note_id}/generate-questions",
                headers=self.get_headers(),
                timeout=30,
            )
            if response.status_code == 200:
                questions_data = response.json()
                self.workflow_content["generated_questions"] = questions_data[
                    "questions"
                ]
                self.log_step(
                    "Step 5",
                    "PASSED",
                    f"Generated {len(questions_data['questions'])} questions",
                )
            else:
                self.log_step(
                    "Step 5", "FAILED", f"Question generation failed: {response.text}"
                )
                return False

            # ===== STEP 6: Answer Integration =====
            self.log_step("Step 6", "STARTING", "Answer integration")

            # Answer one question with the specified answer
            if self.workflow_content.get("generated_questions"):
                questions = self.workflow_content["generated_questions"]
                if len(questions) > 0:
                    # Use the first question
                    question_text = questions[0]
                    answer_text = "在正文后面加十个'。'"

                    update_data = {
                        "question": question_text,
                        "answer": answer_text,
                    }
                    response = requests.post(
                        f"{BASE_URL}/notes/{self.note_id}/update-with-answer",
                        json=update_data,
                        headers=self.get_headers(),
                        timeout=30,
                    )
                    if response.status_code == 200:
                        updated_note_data = response.json()
                        self.workflow_content["updated_note_with_answer"] = (
                            updated_note_data["note"]["content"]
                        )
                        self.workflow_content["input_question"] = question_text
                        self.workflow_content["input_answer"] = answer_text
                        self.log_step(
                            "Step 6", "PASSED", f"Answered question with: {answer_text}"
                        )
                    else:
                        self.log_step(
                            "Step 6",
                            "FAILED",
                            f"Answer integration failed: {response.text}",
                        )
                        return False
                else:
                    self.log_step(
                        "Step 6", "SKIPPED", "No questions available to answer"
                    )
            else:
                self.log_step("Step 6", "FAILED", "No questions generated")
                return False

            # ===== WORKFLOW COMPLETED =====
            self.log_step(
                "Workflow", "COMPLETED", "All workflow steps completed successfully"
            )
            return True

        except Exception as e:
            self.log_step("Workflow", "FAILED", f"Workflow error: {str(e)}")
            return False

    def generate_workflow_report(self):
        """Generate comprehensive workflow report"""
        passed_steps = len([s for s in self.workflow_steps if s["status"] == "PASSED"])
        failed_steps = len([s for s in self.workflow_steps if s["status"] == "FAILED"])
        total_steps = len(self.workflow_steps)

        # Create markdown report
        report_markdown = [
            "# NoteBuddy Backend - Workflow End-to-End Test Report",
            "",
            f"**Generated on:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"**Total Steps:** {total_steps}",
            f"**Passed:** {passed_steps}",
            f"**Failed:** {failed_steps}",
            f"**Success Rate:** {passed_steps/total_steps*100:.1f}%",
            "",
            "## Workflow Overview",
            "",
            "### Step-by-Step Progress",
            "",
            "| Step | Status | Details | Timestamp |",
            "|------|--------|---------|-----------|",
        ]

        for step in self.workflow_steps:
            status_icon = "✅" if step["status"] == "PASSED" else "❌"
            report_markdown.append(
                f"| {step['step_name']} | {status_icon} {step['status']} | {step['details']} | {step['timestamp']} |"
            )

        # Add workflow content section
        report_markdown.extend(
            [
                "",
                "## Workflow Content Generated",
                "",
            ]
        )

        # Add original transcript content
        if "original_transcript" in self.workflow_content:
            report_markdown.extend(
                [
                    "### Original Transcript Content",
                    "```",
                    self.workflow_content["original_transcript"],
                    "```",
                    "",
                ]
            )

        # Add updated transcript content
        if "updated_transcript" in self.workflow_content:
            report_markdown.extend(
                [
                    "### Updated Transcript Content (with 【更新】 prefix)",
                    "```",
                    self.workflow_content["updated_transcript"],
                    "```",
                    "",
                ]
            )

        # Add generated note content
        if "generated_note" in self.workflow_content:
            report_markdown.extend(
                [
                    "### AI-Generated Note Content",
                    "```",
                    self.workflow_content["generated_note"],
                    "```",
                    "",
                ]
            )

        # Add generated questions
        if "generated_questions" in self.workflow_content:
            report_markdown.extend(
                [
                    "### Generated Follow-up Questions",
                    "",
                ]
            )
            for i, question in enumerate(
                self.workflow_content["generated_questions"], 1
            ):
                report_markdown.append(f"{i}. {question}")
            report_markdown.append("")

        # Add input question and answer
        if (
            "input_question" in self.workflow_content
            and "input_answer" in self.workflow_content
        ):
            report_markdown.extend(
                [
                    "### Input Question and Answer",
                    "",
                    f"**Question:** {self.workflow_content['input_question']}",
                    f"**Answer:** {self.workflow_content['input_answer']}",
                    "",
                ]
            )

        # Add updated note with answer
        if "updated_note_with_answer" in self.workflow_content:
            report_markdown.extend(
                [
                    "### Updated Note Content (After Answer Integration)",
                    "```",
                    self.workflow_content["updated_note_with_answer"],
                    "```",
                    "",
                ]
            )

        # Add workflow summary
        report_markdown.extend(
            [
                "## Workflow Summary",
                "",
                "### API Endpoints Tested in Workflow",
                "",
                "#### Authentication",
                "- `POST /auth/register` - User registration",
                "- `POST /auth/login` - User login",
                "",
                "#### Transcript Operations",
                "- `POST /transcripts/` - Create transcript",
                "- `GET /transcripts/{id}` - Get transcript by ID",
                "- `GET /transcripts/` - Get all transcripts",
                "- `PUT /transcripts/{id}` - Update transcript",
                "- `DELETE /transcripts/{id}` - Delete transcript",
                "",
                "#### Note Operations",
                "- `POST /transcripts/{id}/generate-note` - Generate note from transcript",
                "- `GET /notes/{id}` - Get note by ID",
                "- `GET /notes/` - Get all notes",
                "- `PUT /notes/{id}` - Update note",
                "- `POST /notes/{id}/generate-questions` - Generate follow-up questions",
                "- `POST /notes/{id}/update-with-answer` - Update note with answers",
                "",
                "### Workflow Sequence",
                "1. User registration and login",
                "2. Transcript creation with specified Chinese text",
                "3. Transcript retrieval by ID",
                "4. Get all transcripts",
                "5. Update transcript with 【更新】 prefix",
                "6. Create and delete test transcript",
                "7. Generate note from remaining transcript (no timeout)",
                "8. Note retrieval by ID",
                "9. Get all notes",
                "10. Update note",
                "11. Generate follow-up questions",
                "12. Answer one question with specified answer",
                "",
                "### Test Environment",
                f"- **Base URL:** {BASE_URL}",
                "- **Environment:** Test",
                "- **Database:** SQLite (test_notebuddy.db)",
                "- **Authentication:** Email-based JWT tokens",
                "",
                "## Conclusion",
                f"The complete workflow has been executed with {total_steps} steps.",
                f"**{passed_steps} steps passed** and **{failed_steps} steps failed**.",
                "",
            ]
        )

        if failed_steps == 0:
            report_markdown.append(
                "🎉 **Workflow completed successfully! The API workflow is functioning correctly.**"
            )
        else:
            report_markdown.append(
                "⚠️ **Some workflow steps failed. Please review the failed steps above.**"
            )

        # Save markdown report
        report_path = "e2e_workflow_report.md"
        with open(report_path, "w", encoding="utf-8") as f:
            f.write("\n".join(report_markdown))

        # Also save JSON data for programmatic access
        json_report = {
            "summary": {
                "total_steps": total_steps,
                "passed_steps": passed_steps,
                "failed_steps": failed_steps,
                "success_rate": passed_steps / total_steps * 100,
                "timestamp": datetime.now().isoformat(),
            },
            "workflow_steps": self.workflow_steps,
            "workflow_content": self.workflow_content,
        }

        with open("e2e_workflow_results.json", "w", encoding="utf-8") as f:
            json.dump(json_report, f, indent=2, ensure_ascii=False)

        print(f"📊 Workflow report generated: {report_path}")
        print(f"📊 JSON results: e2e_workflow_results.json")

        return passed_steps == total_steps

    def run_workflow(self):
        """Run the complete workflow test"""
        print("🚀 Starting NoteBuddy Workflow End-to-End Test")
        print("=" * 60)

        # Clean up any existing test database
        self.cleanup_test_database()

        # Start test server
        if not self.start_test_server():
            print("❌ Failed to start test server. Aborting workflow.")
            return False

        try:
            # Execute the complete workflow
            success = self.test_workflow()

            # Generate workflow report
            self.generate_workflow_report()

            return success

        finally:
            # Stop the test server
            self.stop_test_server()

            # Clean up test database
            self.cleanup_test_database()


def main():
    """Main function to run the workflow test"""
    tester = EndToEndWorkflowTest()
    success = tester.run_workflow()

    if success:
        print("\n🎉 Workflow Testing Completed Successfully!")
        print("📄 Check the generated report: e2e_workflow_report.md")
    else:
        print("\n❌ Workflow Testing Completed with Failures")
        print("📄 Check the generated report: e2e_workflow_report.md for details")

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
