from rest_framework.routers import DefaultRouter
from .views import AlunoViewSet, OperadorViewSet

router = DefaultRouter()
router.register("alunos", AlunoViewSet)
router.register("operadores", OperadorViewSet)

urlpatterns = router.urls