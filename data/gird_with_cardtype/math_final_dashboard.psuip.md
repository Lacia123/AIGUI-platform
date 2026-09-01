<layout:root>
<layout:column alignItems="stretch">

<textCard>
  <text_title>Prepare for Math Final Exams</text_title>
  <text_subtitle>Today's Review Focus: Operations of Higher-order Function</text_subtitle>
  <cta href="https://example.com/schedule/math-final">✦ View Full Schedule</cta>
</textCard>

<layout:row alignItems="stretch">
<targetStatCard>
  <title>Past Exam Papers</title>
  <preview src="file:///sdcard/Pictures/Camera/20260806/20260806201148.jpg" alt="Past Exam Papers"></preview>
  <text>4</text>
  <caption>PAPERS</caption>
  <subtitle>Past papers</subtitle>
</targetStatCard>
<targetStatCard>
  <title>Error Collection</title>
  <preview src="file:///sdcard/Pictures/Camera/20260806/20260806201223.jpg" alt="Error Collection"></preview>
  <text>32</text>
  <caption>PRACTICE</caption>
  <subtitle>Practice Questions</subtitle>
</targetStatCard>
<targetStatCard>
  <title>Mock Self-test</title>
  <preview src="file:///sdcard/Pictures/Camera/camera_1786008139046.jpg" alt="Mock Self-test"></preview>
  <text>23</text>
  <caption>QUESTIONS</caption>
  <subtitle>Questions</subtitle>
</targetStatCard>
</layout:row>

<layout:column alignItems="stretch">
<layout:row alignItems="stretch">


<targetStatCard>
<title href="ding://router?start_time=1755000000000&end_time=1755007200000&type=pre_exam_mock_self_test">Mock Self-test</title>
<preview src="file:///sdcard/Pictures/Camera/camera_1786008139046.jpg"></preview>
<text>23</text>
<caption>QUESTIONS</caption>
<subtitle>Questions</subtitle>
</targetStatCard>

</layout:row>
</layout:column>

<layout:row alignItems="stretch">

  <showcaseCard>
    <title>数列的极限知识图谱</title>
    <imageTextItem>
      <image src="/images/mock_graph.jpeg" alt="数列的极限知识图谱" href="ding://router?start_time=1755000000000&amp;end_time=1755007200000&amp;type=pre_exam_knowledge_graph"></image>
    </imageTextItem>
  </showcaseCard>

<layout:column alignItems="stretch">
## Today's Review Note

![Review Note](file:///sdcard/Pictures/Camera/camera_1786010698497.jpg)

### Introduction to LCCDEs

A linear constant coefficient differential equation (LCCDE) has the form:

$$a_n y^{(n)} + a_{n-1} y^{(n-1)} + \cdots + a_1 y' + a_0 y = f(x)$$

where each $a_i$ is constant and $f(x)$ is a known forcing function.

### Homogeneous Equations

When $f(x) = 0$, the equation is homogeneous. The general solution $y_h(x)$ comes from the characteristic equation:

$$a_n r^n + a_{n-1} r^{n-1} + \cdots + a_1 r + a_0 = 0$$

**Distinct Real Roots:** $y_h(x) = C_1 e^{r_1 x} + \cdots + C_n e^{r_n x}$

**Repeated Real Roots:** If $r$ has multiplicity $k$, include $e^{rx}$, $xe^{rx}$, up to $x^{k-1}e^{rx}$.

**Complex Conjugate Roots:** Include $e^{\alpha x}\cos(\beta x)$ and $e^{\alpha x}\sin(\beta x)$.
</layout:column>

  <mistakesCard>
    <title>Weak Spots</title>
    <preview src="file:///sdcard/Pictures/Camera/camera_1786013999770.jpg"></preview>
    <mistakesCardItem type="error">
      <title>Multivariable Calculus</title>
      <text>38% Mastery</text>
      <caption>12 Mistakes</caption>
    </mistakesCardItem>
    <mistakesCardItem type="warning">
      <title>Linear Algebra (Matrix)</title>
      <text>52% Mastery</text>
      <caption>8 Mistakes</caption>
    </mistakesCardItem>
    <mistakesCardItem type="normal">
      <title>Vector Spaces</title>
      <text>61% Mastery</text>
      <caption>5 Mistakes</caption>
    </mistakesCardItem>
  </mistakesCard>
</layout:row>

</layout:column>
</layout:root>
