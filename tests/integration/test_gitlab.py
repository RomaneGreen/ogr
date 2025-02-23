import os
import unittest

from ogr.services.gitlab import GitlabService
from ogr.persistent_storage import PersistentObjectStorage

DATA_DIR = "test_data"
PERSISTENT_DATA_PREFIX = os.path.join(
    os.path.dirname(os.path.realpath(__file__)), DATA_DIR
)


class GitlabTests(unittest.TestCase):
    def setUp(self):
        self.token = os.environ.get("GITLAB_TOKEN")
        self.user = os.environ.get("GITLAB_USER")
        test_name = self.id() or "all"

        persistent_data_file = os.path.join(
            PERSISTENT_DATA_PREFIX, f"test_gitlab_data_{test_name}.yaml"
        )
        PersistentObjectStorage().storage_file = persistent_data_file

        if PersistentObjectStorage().is_write_mode and (
            not self.user or not self.token
        ):
            raise EnvironmentError("please set GITLAB_TOKEN GITLAB_USER env variables")
        else:
            self.token = "some_token"

        self.service = GitlabService(
            token=self.token, instance_url="https://gitlab.gnome.org", ssl_verify=True
        )

        self.project = self.service.get_project(
            repo="testing-ogr-repo", namespace="lbarcziova"
        )

    def tearDown(self):
        PersistentObjectStorage().dump()


class GenericCommands(GitlabTests):
    def test_branches(self):
        branches = self.project.get_branches()
        assert branches
        assert "master" in branches

    def test_get_file(self):
        file_content = self.project.get_file_content("README.md")
        assert file_content
        assert "This is new README for testing-ogr-repo" in file_content

    def test_nonexisting_file(self):
        with self.assertRaises(FileNotFoundError):
            self.project.get_file_content(".blablabla_nonexisting_file")

    def test_username(self):
        # check just lenght, because it is based who regenerated data files
        assert len(self.service.user.get_username()) > 3

    def test_email(self):
        email = self.service.user.get_email()
        assert email
        assert len(email) > 3
        assert "@" in email
        assert "." in email


class Issues(GitlabTests):
    def test_get_issue_list(self):
        issue_list = self.project.get_issue_list()
        assert issue_list
        assert len(issue_list) >= 1

    def test_issue_info(self):
        issue_info = self.project.get_issue_info(issue_id=1)
        assert issue_info
        assert issue_info.title.startswith("My first issue")
        assert issue_info.description.startswith("This is testing issue")

    def test_get_all_issue_comments(self):
        comments = self.project._get_all_issue_comments(issue_id=2)
        assert comments[0].comment.startswith("Comment")
        assert comments[0].author == "lbarcziova"
        assert len(comments) == 2

    def test_create_issue(self):
        issue = self.project.create_issue(
            title="Issue 2", description="Description for issue 2"
        )
        assert issue.title == "Issue 2"
        assert issue.description == "Description for issue 2"

    def test_close_issue(self):
        issue = self.project.close_issue(issue_id=1)
        assert issue.status == "closed"


class PullRequests(GitlabTests):
    def test_pr_list(self):
        pr_list = self.project.list_pull_requests()
        count = len(pr_list)
        assert pr_list
        assert count >= 1
        assert pr_list[count - 1].title == "change"

    def test_pr_info(self):
        pr_info = self.project.get_pr_info(pr_id=1)
        assert pr_info
        assert pr_info.title == "change"
        assert pr_info.description == "description of mergerequest"

    def test_get_all_pr_commits(self):
        commits = self.project.get_all_pr_commits(pr_id=1)
        assert commits[0] == "0709030b613d56752725c33df36041c2b7610506"
        assert commits[1] == "f3881188db863e4e053f5a82422f067ac9ba2594"
        assert len(commits) == 2

    def test_get_all_pr_comments(self):
        comments = self.project._get_all_pr_comments(pr_id=1)
        count = len(comments)
        assert comments[count - 1].comment == "first comment of mergerequest"
        assert comments[count - 1].author == "lbarcziova"
        assert count == 5

    def test_update_pr_info(self):
        pr_info = self.project.get_pr_info(pr_id=1)
        original_description = pr_info.description

        self.project.update_pr_info(pr_id=1, description="changed description")
        pr_info = self.project.get_pr_info(pr_id=1)
        assert pr_info.description == "changed description"

        self.project.update_pr_info(pr_id=1, description=original_description)
        pr_info = self.project.get_pr_info(pr_id=1)
        assert pr_info.description == original_description


class Tags(GitlabTests):
    def test_get_tags(self):
        tags = self.project.get_tags()
        count = len(tags)
        assert count >= 2
        assert tags[count - 1].name == "0.1.0"
        assert tags[count - 1].commit_sha == "957d267a5b0cd9e615cd081c0eb02397dce1eb73"

    def test_tag_from_tag_name(self):
        tag = self.project._git_tag_from_tag_name(tag_name="0.1.0")
        assert tag.commit_sha == "957d267a5b0cd9e615cd081c0eb02397dce1eb73"


class Releases(GitlabTests):
    def test_create_release(self):
        count_before = len(self.project.get_releases())
        release = self.project.create_release(
            name="test", tag_name="0.2.0", description="testing release", ref="master"
        )
        count_after = len(self.project.get_releases())
        assert release.tag_name == "0.2.0"
        assert release.title == "test"
        assert release.body == "testing release"
        assert count_before + 1 == count_after

    def test_get_releases(self):
        releases = self.project.get_releases()
        assert releases
        count = len(releases)
        assert count >= 1
        assert releases[count - 1].title == "test"
        assert releases[count - 1].tag_name == "0.1.0"
        assert releases[count - 1].body == "testing release"
