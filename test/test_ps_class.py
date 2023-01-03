from libps import Picoscope
from matplotlib import pyplot as plt

my_ps = Picoscope.Picoscope("IW982/0073")

print(my_ps.serial)

my_ps.setChn("A", 1, "dc", 5, 0)
my_ps.setChn("B", 1, "dc", 5, 0)

my_ps.setSimpleTrigger("A", 2, "RISING", 0, 1000)

preTrigSamples, postTrigSamples, timebase, interval_ns = my_ps.getSamplesToCapture(-0.2, 0.2, 0.001)

res = my_ps.acquireBlock(preTrigSamples, postTrigSamples, timebase, interval_ns)

print(res.keys())
t = res["time"]

d1 = res["A"]
d2 = res["B"]

plt.figure()
plt.plot(t, d1)
plt.plot(t, d2)
plt.show()
