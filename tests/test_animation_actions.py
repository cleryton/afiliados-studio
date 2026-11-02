import math
import unittest
from animation_action_math import leg_angles,step_target,walk_y


class ActionMotionTests(unittest.TestCase):
    def test_stance_feet_remain_planted_as_character_moves(self):
        for phase in (0,.6):
            previous=None
            for frame in range(109):
                t=frame/18;position,height,stance=step_target(t,phase)
                self.assertGreaterEqual(height,-1e-9)
                if stance:
                    self.assertEqual(height,0)
                    if previous is not None:self.assertAlmostEqual(position,previous,places=8)
                    previous=position
                else:previous=None
        self.assertGreater(walk_y(3),walk_y(0));self.assertEqual(walk_y(6),walk_y(3.6))
        for phase in (0,.6):self.assertEqual(step_target(6,phase),(walk_y(3.6),0.,True))

    def test_leg_inverse_kinematics_reaches_swing_and_contact_targets(self):
        lower=math.hypot(.065,.53)
        for frame in range(109):
            t=frame/18
            for phase in (0,.6):
                foot,height,_=step_target(t,phase)
                y=-(foot-walk_y(t));z=.12+height-1.10
                hip,knee=leg_angles(y,z,.51,lower)
                self.assertAlmostEqual(.51*math.sin(hip)+lower*math.sin(hip+knee),y,places=7)
                self.assertAlmostEqual(-.51*math.cos(hip)-lower*math.cos(hip+knee),z,places=7)

    def test_impossible_targets_fail_without_stretching_body_proportions(self):
        for y,z in ((0,0),(0,-2),(3,-1)):
            with self.subTest(target=(y,z)),self.assertRaises(ValueError):leg_angles(y,z)


if __name__=='__main__':unittest.main()
