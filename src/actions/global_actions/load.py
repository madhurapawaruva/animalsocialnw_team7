from ..action import GlobalAction
from ...static import PageState


class Load(GlobalAction):

    def do(self):
        PageState.landing_page.show()
